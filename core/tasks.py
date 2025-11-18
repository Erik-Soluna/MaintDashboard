from celery import shared_task
import logging
import json
import requests
import subprocess
import os
import time
from datetime import datetime, timedelta
from .models import PortainerConfig
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def celery_beat_heartbeat():
    logger.info("Celery Beat heartbeat task ran.")

def get_git_info():
    """
    Get current git commit hash and date.
    """
    try:
        # Get current commit hash
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], 
            cwd=os.getcwd(), 
            stderr=subprocess.PIPE,
            text=True
        ).strip()
        
        # Get commit date
        commit_date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%cd', '--date=iso'], 
            cwd=os.getcwd(), 
            stderr=subprocess.PIPE,
            text=True
        ).strip()
        
        return commit_hash, commit_date
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git command failed: {e}")
        return None, None
    except Exception as e:
        logger.warning(f"Error getting git info: {e}")
        return None, None

def check_for_changes(config):
    """
    Check if there are new commits since last update.
    """
    try:
        current_hash, current_date = get_git_info()
        
        if not current_hash:
            logger.warning("Could not get current git info, proceeding with update")
            return True, current_hash, current_date
        
        # If we don't have a previous hash, this is the first run
        if not config.last_commit_hash:
            logger.info(f"First run - setting initial commit hash: {current_hash[:8] if current_hash else 'unknown'}")
            return True, current_hash, current_date
        
        # Check if hash has changed
        if current_hash != config.last_commit_hash:
            logger.info(f"New commit detected: {current_hash[:8] if current_hash else 'unknown'} (was: {config.last_commit_hash[:8] if config.last_commit_hash else 'unknown'})")
            return True, current_hash, current_date
        else:
            logger.info(f"No new commits since last update (current: {current_hash[:8] if current_hash else 'unknown'})")
            return False, current_hash, current_date
            
    except Exception as e:
        logger.error(f"Error checking for changes: {e}")
        return True, None, None  # Proceed with update if we can't check

@shared_task
def auto_update_portainer_stack():
    """
    Automatically check for and pull the newest version based on polling frequency.
    Only updates if there are new commits.
    """
    try:
        config = PortainerConfig.get_config()
        
        # Check if polling is enabled
        if not config.polling_frequency or config.polling_frequency == 'disabled':
            logger.info("Auto-update polling is disabled")
            return {'status': 'disabled'}
        
        # Check if webhook URL is configured
        if not config.portainer_url:
            logger.warning("Auto-update failed: No webhook URL configured")
            return {'status': 'error', 'message': 'No webhook URL configured'}
        
        # Check for changes first
        has_changes, current_hash, current_date = check_for_changes(config)
        
        if not has_changes:
            # Update last check date even if no changes
            config.last_check_date = timezone.now()
            config.save(update_fields=['last_check_date'])
            return {
                'status': 'no_changes', 
                'message': 'No new commits detected, skipping update',
                'commit_hash': current_hash[:8] if current_hash else None
            }
        
        # Get image tag (default to 'latest')
        image_tag = config.image_tag or 'latest'
        
        # Build webhook URL with tag parameter
        webhook_url_with_tag = f"{config.portainer_url}?tag={image_tag}"
        
        # Prepare headers with webhook secret if available
        headers = {}
        if config.webhook_secret:
            headers['X-Webhook-Secret'] = config.webhook_secret
        
        logger.info(f"Changes detected - auto-updating stack with tag '{image_tag}' via webhook")
        
        # Call the webhook URL to trigger stack update
        webhook_response = requests.post(
            webhook_url_with_tag,
            headers=headers,
            json={
                'action': 'auto_update', 
                'timestamp': timezone.now().isoformat(),
                'commit_hash': current_hash,
                'commit_date': current_date
            },
            timeout=30
        )
        
        logger.info(f"Auto-update webhook response status: {webhook_response.status_code}")
        
        if webhook_response.status_code in [200, 202, 204]:
            logger.info("Auto-update successful")
            
            # Update our tracking info
            config.last_commit_hash = current_hash
            config.last_commit_date = timezone.now()  # Use current time as commit date
            config.last_check_date = timezone.now()
            config.save(update_fields=['last_commit_hash', 'last_commit_date', 'last_check_date'])
            
            return {
                'status': 'success', 
                'message': f'Auto-update triggered successfully with tag {image_tag} (commit: {current_hash[:8] if current_hash else "unknown"})',
                'response_code': webhook_response.status_code,
                'commit_hash': current_hash[:8] if current_hash else None
            }
        else:
            logger.error(f"Auto-update failed with status: {webhook_response.status_code}")
            return {
                'status': 'error', 
                'message': f'Auto-update failed: {webhook_response.status_code}',
                'response_code': webhook_response.status_code
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in auto-update: {str(e)}")
        return {'status': 'error', 'message': f'Network error: {str(e)}'}
    except Exception as e:
        logger.error(f"Unexpected error in auto-update: {str(e)}")
        return {'status': 'error', 'message': f'Error: {str(e)}'}

@shared_task
def collect_docker_logs():
    """
    Collect Docker logs from all containers and write them to files.
    This task runs periodically to maintain log files that can be read by the web interface.
    """
    try:
        # Create logs directory if it doesn't exist
        logs_dir = '/app/logs'
        os.makedirs(logs_dir, exist_ok=True)
        
        # Get list of containers using docker ps
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}\t{{.ID}}\t{{.Image}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning(f"Docker ps failed: {result.stderr}")
                return {'status': 'error', 'message': 'Docker ps failed'}
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        containers.append({
                            'name': parts[0].strip(),
                            'id': parts[1].strip(),
                            'image': parts[2].strip()
                        })
            
            logger.info(f"Found {len(containers)} containers")
            
        except subprocess.TimeoutExpired:
            logger.error("Docker ps command timed out")
            return {'status': 'error', 'message': 'Docker ps timed out'}
        except FileNotFoundError:
            logger.error("Docker CLI not available")
            return {'status': 'error', 'message': 'Docker CLI not available'}
        
        # Collect logs for each container
        collected_logs = {}
        for container in containers:
            try:
                # Get logs for this container
                log_result = subprocess.run(
                    ['docker', 'logs', '--tail', '100', container['name']],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if log_result.returncode == 0:
                    # Write logs to file
                    log_file = os.path.join(logs_dir, f"{container['name']}.log")
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Container: {container['name']}\n")
                        f.write(f"# Image: {container['image']}\n")
                        f.write(f"# ID: {container['id']}\n")
                        f.write(f"# Collected at: {datetime.now().isoformat()}\n")
                        f.write("#" * 80 + "\n")
                        f.write(log_result.stdout)
                    
                    collected_logs[container['name']] = {
                        'status': 'success',
                        'lines': len(log_result.stdout.split('\n')),
                        'file': log_file
                    }
                    lines_count = len(log_result.stdout.split('\n'))
                    logger.info(f"Collected logs for {container['name']}: {lines_count} lines")
                else:
                    collected_logs[container['name']] = {
                        'status': 'error',
                        'error': log_result.stderr
                    }
                    logger.warning(f"Failed to get logs for {container['name']}: {log_result.stderr}")
                    
            except subprocess.TimeoutExpired:
                collected_logs[container['name']] = {
                    'status': 'error',
                    'error': 'Timeout getting logs'
                }
                logger.warning(f"Timeout getting logs for {container['name']}")
            except Exception as e:
                collected_logs[container['name']] = {
                    'status': 'error',
                    'error': str(e)
                }
                logger.error(f"Error getting logs for {container['name']}: {e}")
        
        # Write summary file
        summary_file = os.path.join(logs_dir, 'collection_summary.json')
        summary = {
            'timestamp': datetime.now().isoformat(),
            'containers_processed': len(containers),
            'containers_successful': len([c for c in collected_logs.values() if c['status'] == 'success']),
            'containers_failed': len([c for c in collected_logs.values() if c['status'] == 'error']),
            'results': collected_logs
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Docker logs collection completed: {summary['containers_successful']} successful, {summary['containers_failed']} failed")
        
        return {
            'status': 'success',
            'message': f'Collected logs for {summary["containers_successful"]} containers',
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error in collect_docker_logs task: {e}")
        return {'status': 'error', 'message': str(e)}

@shared_task
def collect_system_logs():
    """
    Collect system logs and write them to files.
    """
    try:
        logs_dir = '/app/logs'
        os.makedirs(logs_dir, exist_ok=True)
        
        system_logs = {}
        
        # Common system log paths
        log_paths = [
            '/var/log/syslog',
            '/var/log/messages',
            '/var/log/dmesg',
            '/proc/1/fd/1',  # Docker container stdout
            '/proc/1/fd/2',  # Docker container stderr
        ]
        
        for log_path in log_paths:
            try:
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        
                    # Write to our logs directory
                    filename = os.path.basename(log_path)
                    if filename == 'fd':
                        filename = f"container_{log_path.split('/')[-1]}.log"
                    
                    log_file = os.path.join(logs_dir, f"system_{filename}")
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write(f"# System Log: {log_path}\n")
                        f.write(f"# Collected at: {datetime.now().isoformat()}\n")
                        f.write("#" * 80 + "\n")
                        f.write(content)
                    
                    system_logs[log_path] = {
                        'status': 'success',
                        'lines': len(content.split('\n')),
                        'file': log_file
                    }
                else:
                    system_logs[log_path] = {
                        'status': 'not_found',
                        'error': 'File does not exist'
                    }
                    
            except Exception as e:
                system_logs[log_path] = {
                    'status': 'error',
                    'error': str(e)
                }
                logger.warning(f"Error reading system log {log_path}: {e}")
        
        # Write system logs summary
        summary_file = os.path.join(logs_dir, 'system_logs_summary.json')
        summary = {
            'timestamp': datetime.now().isoformat(),
            'logs_processed': len(log_paths),
            'logs_successful': len([l for l in system_logs.values() if l['status'] == 'success']),
            'logs_failed': len([l for l in system_logs.values() if l['status'] == 'error']),
            'results': system_logs
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"System logs collection completed: {summary['logs_successful']} successful, {summary['logs_failed']} failed")
        
        return {
            'status': 'success',
            'message': f'Collected {summary["logs_successful"]} system logs',
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error in collect_system_logs task: {e}")
        return {'status': 'error', 'message': str(e)}

@shared_task
def update_version_info():
    """Automatically update version information from git"""
    try:
        import importlib.util
        from django.conf import settings
        
        spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
        version_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version_module)
        import json
        import os
        
        # Get current version info
        version_info = version_module.get_git_version()
        
        # Update version.json file
        with open('version.json', 'w') as f:
            json.dump(version_info, f, indent=2)
        
        # Update .env file if it exists
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            # Update version-related lines
            lines = env_content.split('\n')
            updated_lines = []
            
            for line in lines:
                if line.startswith('GIT_COMMIT_COUNT='):
                    updated_lines.append(f'GIT_COMMIT_COUNT={version_info["commit_count"]}')
                elif line.startswith('GIT_COMMIT_HASH='):
                    updated_lines.append(f'GIT_COMMIT_HASH={version_info["commit_hash"]}')
                elif line.startswith('GIT_BRANCH='):
                    updated_lines.append(f'GIT_BRANCH={version_info["branch"]}')
                elif line.startswith('GIT_COMMIT_DATE='):
                    updated_lines.append(f'GIT_COMMIT_DATE={version_info["commit_date"]}')
                else:
                    updated_lines.append(line)
            
            # Write updated content
            with open(env_file, 'w') as f:
                f.write('\n'.join(updated_lines))
        
        logger.info(f"Version info updated: {version_info['full_version']}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating version info: {str(e)}")
        return False


@shared_task
def set_manual_version(commit_count, commit_hash, branch, commit_date):
    """Set version information manually via Celery task"""
    try:
        import json
        import os
        
        # Ensure commit_count is a valid integer
        try:
            commit_count_int = int(commit_count)
            if commit_count_int <= 0:
                commit_count_int = 1  # Fallback to 1 if invalid
        except (ValueError, TypeError):
            commit_count_int = 1  # Fallback to 1 if conversion fails
        
        # Validate and format commit_date
        try:
            from datetime import datetime
            # Try to parse the date and format it consistently
            if isinstance(commit_date, str):
                # Try different date formats
                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                parsed_date = None
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(commit_date, fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_date:
                    commit_date = parsed_date.strftime('%Y-%m-%d')
                else:
                    # If all formats fail, use today's date
                    commit_date = datetime.now().strftime('%Y-%m-%d')
            else:
                commit_date = str(commit_date)
        except Exception:
            # Fallback to today's date if date parsing fails
            commit_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create version data
        version_data = {
            'commit_count': commit_count_int,
            'commit_hash': str(commit_hash),
            'branch': str(branch),
            'commit_date': str(commit_date),
            'version': f'v{commit_count_int}.{commit_hash}',
            'full_version': f'v{commit_count_int}.{commit_hash} ({branch}) - {commit_date}'
        }
        
        # Update version.json
        with open('version.json', 'w') as f:
            json.dump(version_data, f, indent=2)
        
        # Update .env file
        env_file = '.env'
        env_content = f"""# Version Information (Auto-generated)
GIT_COMMIT_COUNT={commit_count_int}
GIT_COMMIT_HASH={commit_hash}
GIT_BRANCH={branch}
GIT_COMMIT_DATE={commit_date}

# Other environment variables can be added below
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"Manual version set: {version_data['full_version']}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting manual version: {str(e)}")
        return False