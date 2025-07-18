# Database User Authentication Fix

## 🔍 Problem Analysis

The error you're experiencing is a PostgreSQL authentication failure:

```
psql: error: connection to server at "db" (172.18.0.3), port 5432 failed: FATAL: password authentication failed for user "maintenance_user"
```

### Root Cause

The issue occurs because:

1. **Environment Configuration**: Your `env.production` file specifies:
   ```env
   DB_USER=maintenance_user
   DB_PASSWORD=SecureProdPassword2024!
   ```

2. **PostgreSQL Container**: The PostgreSQL container is initialized with the default `postgres` user, but the `maintenance_user` is never created.

3. **Missing User**: The application tries to connect as `maintenance_user`, but this user doesn't exist in the database.

## 🛠️ Solutions

### Solution 1: Quick Fix (Recommended)

Run the database user fix script inside the database container:

```bash
# Copy the fix script to the database container
docker cp fix-database-user-docker.sh maintenance_db:/tmp/

# Execute the script inside the database container
docker exec -it maintenance_db bash /tmp/fix-database-user-docker.sh
```

### Solution 2: Manual Database Commands

Connect to the database container and run the commands manually:

```bash
# Connect to the database container
docker exec -it maintenance_db bash

# Connect to PostgreSQL as postgres user
psql -U postgres

# Create the maintenance_user
CREATE USER maintenance_user WITH PASSWORD 'SecureProdPassword2024!';

# Create the database if it doesn't exist
CREATE DATABASE maintenance_dashboard_prod;

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard_prod TO maintenance_user;
\c maintenance_dashboard_prod
GRANT ALL PRIVILEGES ON SCHEMA public TO maintenance_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO maintenance_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO maintenance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO maintenance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO maintenance_user;

# Exit PostgreSQL
\q

# Test the connection
PGPASSWORD=SecureProdPassword2024! psql -U maintenance_user -d maintenance_dashboard_prod -c "SELECT 1;"
```

### Solution 3: Use Default PostgreSQL User (Temporary)

If you need a quick fix to get the application running, you can temporarily modify the environment to use the default `postgres` user:

```bash
# Edit env.production
DB_USER=postgres
DB_PASSWORD=postgres
```

**Note**: This is not recommended for production as it uses the default credentials.

### Solution 4: Automated Fix Script

Use the external fix script (if you have access to the host):

```bash
# Set environment variables
export DB_NAME=maintenance_dashboard_prod
export DB_USER=maintenance_user
export DB_PASSWORD=SecureProdPassword2024!
export DB_HOST=localhost
export DB_PORT=5432

# Run the fix script
./fix-database-user.sh
```

## 🔄 Restart Application

After fixing the database user, restart your application containers:

```bash
# Restart the web container
docker-compose restart web

# Or restart all containers
docker-compose restart
```

## ✅ Verification

To verify the fix worked:

```bash
# Test connection from host
PGPASSWORD=SecureProdPassword2024! psql -h localhost -p 5432 -U maintenance_user -d maintenance_dashboard_prod -c "SELECT 1;"

# Check container logs
docker-compose logs web

# Test the application
curl http://localhost:4405/core/health/simple/
```

## 🛡️ Security Considerations

1. **Strong Passwords**: Use strong, unique passwords for database users
2. **Limited Privileges**: Consider granting only necessary privileges instead of ALL
3. **Network Security**: Ensure database is not exposed to external networks
4. **Environment Variables**: Store sensitive data in environment variables, not in code

## 🔧 Prevention

To prevent this issue in the future:

1. **Database Initialization**: Include user creation in your database initialization scripts
2. **Docker Compose**: Consider using PostgreSQL initialization scripts
3. **Documentation**: Document the required database setup steps
4. **Testing**: Test database connections during the build process

## 📋 PostgreSQL Initialization Script

Create a file `init-db.sql` in your project:

```sql
-- Create the maintenance_user
CREATE USER maintenance_user WITH PASSWORD 'SecureProdPassword2024!';

-- Create the database
CREATE DATABASE maintenance_dashboard_prod;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard_prod TO maintenance_user;
```

Then modify your `docker-compose.yml` to include this initialization script:

```yaml
services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data/
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
```

## 🆘 Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the script has execute permissions
2. **Container Not Found**: Check if the container name matches your setup
3. **Network Issues**: Verify the database container is accessible
4. **Password Issues**: Double-check the password matches the environment file

### Debug Commands

```bash
# Check container status
docker-compose ps

# View database logs
docker-compose logs db

# Check network connectivity
docker exec maintenance_db pg_isready -U postgres

# List all users in PostgreSQL
docker exec -it maintenance_db psql -U postgres -c "\du"
```

## 📞 Support

If you continue to experience issues:

1. Check the container logs: `docker-compose logs`
2. Verify environment variables: `docker-compose config`
3. Test database connectivity manually
4. Review the PostgreSQL documentation for your specific version