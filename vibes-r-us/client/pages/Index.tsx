import { ChevronDown, User } from "lucide-react";

const MaintenanceItem = ({
  date,
  time,
  item,
  customer,
  downtime,
  outstanding,
  borderColor = "transparent"
}: {
  date: string;
  time: string;
  item: string;
  customer: string;
  downtime: string;
  outstanding: string;
  borderColor?: string;
}) => (
  <div className="flex">
    <div className="flex w-auto h-auto p-2 flex-col items-center justify-center gap-2 rounded-l-md bg-black self-stretch">
      <div className="text-white text-center text-base font-normal">{date}</div>
      <div className="text-white text-center text-sm font-light">{time}</div>
    </div>
    <div 
      className="flex flex-1 p-3 pl-5 items-center gap-2 rounded-r-md bg-dashboard-card"
      style={{ 
        borderTop: borderColor !== "transparent" ? `1px solid ${borderColor}` : "none",
        borderRight: borderColor !== "transparent" ? `1px solid ${borderColor}` : "none", 
        borderBottom: borderColor !== "transparent" ? `1px solid ${borderColor}` : "none"
      }}
    >
      <div className="flex flex-col justify-center items-start gap-3 flex-1">
        <div className="text-white text-base font-normal self-stretch">{item}</div>
        <div className="text-white text-base font-normal self-stretch">{customer}</div>
        <div className="text-white text-base font-normal self-stretch">{downtime}</div>
        <div className="text-white text-base font-normal self-stretch">{outstanding}</div>
      </div>
    </div>
  </div>
);

const StatusBadge = ({ status, type }: { status: string; type: "urgent" | "warning" | "healthy" | "offline" }) => {
  const colorMap = {
    urgent: "bg-status-urgent",
    warning: "bg-status-warning", 
    healthy: "bg-status-healthy",
    offline: "bg-status-offline"
  };
  
  return (
    <div className={`w-20 h-5 rounded-lg ${colorMap[type]} flex items-center justify-center`}>
      <span className="text-white text-center text-sm font-bold">{status}</span>
    </div>
  );
};

const EquipmentCard = ({ 
  name, 
  status, 
  statusType, 
  downtimes, 
  equipmentInRepair 
}: { 
  name: string; 
  status: string; 
  statusType: "urgent" | "warning" | "healthy" | "offline";
  downtimes?: Array<{ company: string; datetime: string }>;
  equipmentInRepair?: string;
}) => (
  <div className="flex flex-col justify-center items-center gap-2 flex-1">
    <div className="flex justify-between items-center self-stretch">
      <div className="text-white text-2xl font-bold">{name}</div>
      <StatusBadge status={status} type={statusType} />
    </div>
    
    <div className="flex h-52 p-0 px-3 flex-col items-start gap-3 self-stretch rounded-md bg-dashboard-card">
      <div className="flex py-3 items-center gap-2">
        <div className="text-white text-base font-bold">Scheduled Downtimes</div>
      </div>
      {downtimes?.map((downtime, idx) => (
        <div key={idx} className="flex flex-col justify-center items-start self-stretch">
          <div className="text-white text-sm font-normal self-stretch">{downtime.company}</div>
          <div className="text-white text-sm font-light self-stretch">{downtime.datetime}</div>
        </div>
      ))}
    </div>
    
    <div className="flex h-20 p-1 px-3 flex-col justify-center items-start gap-2 self-stretch rounded-md bg-dashboard-card">
      <div className="flex flex-col items-start gap-2 flex-1">
        <div className="text-white text-base font-bold">Equipment In Repair</div>
        {equipmentInRepair && (
          <div className="text-status-linkBlue text-sm font-light underline cursor-pointer">
            {equipmentInRepair}
          </div>
        )}
      </div>
    </div>
  </div>
);

export default function Index() {
  const statsData = [
    { label: "Active Equipment", value: "0" },
    { label: "Pending Maintenance", value: "0" },
    { label: "Overdue Items", value: "0" },
    { label: "Events This Week", value: "0" },
    { label: "Completed This Month", value: "0" }
  ];

  const urgentItems = [
    {
      date: "09-28",
      time: "13:30",
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A",
      borderColor: "#FF0000"
    },
    {
      date: "09-28", 
      time: "13:30",
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital", 
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A",
      borderColor: "#FF0000"
    },
    {
      date: "09-28",
      time: "13:30", 
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A", 
      outstanding: "Outstanding: N/A",
      borderColor: "#FF0000"
    },
    {
      date: "09-28",
      time: "13:30",
      item: "Item: DGA Oil Sample", 
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A", 
      borderColor: "#C6AB00"
    },
    {
      date: "09-28",
      time: "13:30",
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A",
      borderColor: "#C6AB00" 
    }
  ];

  const upcomingItems = [
    {
      date: "09-28",
      time: "13:30", 
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A"
    },
    {
      date: "09-28",
      time: "13:30",
      item: "Item: DGA Oil Sample", 
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A"
    },
    {
      date: "09-28", 
      time: "13:30",
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A"
    },
    {
      date: "09-28",
      time: "13:30",
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital", 
      downtime: "Est. Downtime: N/A",
      outstanding: "Outstanding: N/A"
    },
    {
      date: "09-28",
      time: "13:30",
      item: "Item: DGA Oil Sample",
      customer: "Customer: Bit Digital",
      downtime: "Est. Downtime: N/A", 
      outstanding: "Outstanding: N/A"
    }
  ];

  return (
    <div className="flex w-full min-h-screen flex-col items-start bg-dashboard-background">
      {/* Header Navigation */}
      <div className="flex min-w-full px-9 py-7 justify-center items-center gap-3 bg-dashboard-header">
        <div className="flex h-11 px-8 justify-between items-center flex-1">
          {/* Logo and Title */}
          <div className="flex items-center gap-6">
            <svg className="w-44 h-8" viewBox="0 0 175 33" fill="none" xmlns="http://www.w3.org/2000/svg">
              <g clipPath="url(#clip0_827_4)">
                <path d="M0.537893 27.3176C1.23088 26.8562 1.98657 27.1199 2.65977 27.6736C3.39896 28.2834 4.12825 28.8931 4.94663 29.3249C6.17422 29.9742 7.5701 30.3005 9.13758 30.3005C10.1144 30.3005 11.0285 30.1522 11.8864 29.8589C12.7444 29.5622 13.4902 29.1502 14.1271 28.6196C14.764 28.0889 15.2656 27.4462 15.6352 26.6914C16.0048 25.9366 16.1896 25.0895 16.1896 24.1435C16.1896 23.0525 15.9619 22.1494 15.5032 21.4408C15.0445 20.7321 14.4307 20.1487 13.6618 19.6906C12.8929 19.2324 12.0283 18.8402 11.0681 18.5172C10.1078 18.1909 9.11778 17.8679 8.09479 17.5416C7.07181 17.2152 6.08512 16.8461 5.12153 16.4341C4.16125 16.0221 3.29666 15.4815 2.52777 14.8157C1.75888 14.1532 1.14508 13.316 0.686391 12.314C0.227697 11.3087 0 10.0694 0 8.59279C0 7.20515 0.273896 5.97243 0.821689 4.89463C1.36948 3.81682 2.10867 2.917 3.03926 2.19187C3.96985 1.47004 5.04233 0.922893 6.25342 0.553735C7.4645 0.184578 8.73829 0 10.0682 0C11.7841 0 13.3714 0.303236 14.8366 0.909708C15.7738 1.29864 16.6087 1.83919 17.2885 2.65002C17.9056 3.38504 17.9254 4.29804 17.4073 4.76938C16.7803 5.22093 16.1764 5.22423 15.3712 4.69686C14.7442 4.28486 14.1337 3.76079 13.5067 3.43118C12.5167 2.9137 11.3387 2.65661 9.97907 2.65661C9.03198 2.65661 8.13109 2.78186 7.2731 3.03236C6.41512 3.28286 5.66933 3.65202 5.03243 4.13983C4.39554 4.62765 3.88735 5.24071 3.50125 5.97902C3.11846 6.71734 2.92376 7.58749 2.92376 8.59279C2.92376 10.1584 3.32306 11.3615 4.12165 12.202C4.92024 13.0424 5.91682 13.7083 7.11471 14.1961C8.31259 14.6839 9.61277 15.1124 11.0186 15.4815C12.421 15.8507 13.7245 16.3451 14.9224 16.9647C16.1203 17.5844 17.1169 18.448 17.9155 19.5554C18.7141 20.6629 19.1133 22.1923 19.1133 24.1402C19.1133 25.5575 18.8461 26.8133 18.3148 27.9043C17.7835 28.9986 17.0641 29.9215 16.1632 30.673C15.2623 31.4245 14.2195 31.9947 13.0348 32.3803C11.8534 32.7627 10.6259 32.9571 9.35208 32.9571C7.283 32.9571 5.33603 32.6605 3.64975 31.8134C2.46177 31.2135 1.62358 30.7587 0.73589 29.7369C0.0626992 28.9623 -0.244197 27.9801 0.501593 27.3374L0.534593 27.3176H0.537893Z" fill="white"/>
                <path d="M76.9051 32.9606H66.2925C62.8968 32.9606 60.1348 30.2018 60.1348 26.8101V1.41742C60.1348 0.64285 60.7618 0.0166016 61.5372 0.0166016C62.3127 0.0166016 62.9397 0.64285 62.9397 1.41742V26.8101C62.9397 28.6559 64.4445 30.1589 66.2925 30.1589H76.9051C77.6806 30.1589 78.3076 30.7852 78.3076 31.5597C78.3076 32.3343 77.6806 32.9606 76.9051 32.9606Z" fill="white"/>
                <path d="M38.7712 32.9996C37.339 32.9996 35.8969 32.8118 34.4746 32.4294C30.2177 31.289 26.6636 28.5632 24.4593 24.7529C22.2549 20.9427 21.6708 16.4996 22.8126 12.2477C23.9544 7.99584 26.6801 4.44271 30.4982 2.24095C38.3752 -2.3043 48.4797 0.401757 53.027 8.27271C55.2314 12.0829 55.8155 16.526 54.6737 20.7779C53.5319 25.0298 50.8061 28.5829 46.9881 30.7847C44.4471 32.2514 41.6256 32.9996 38.7679 32.9996H38.7712ZM31.9007 4.67013C25.3635 8.44081 23.1162 16.8227 26.8913 23.3521C30.6665 29.8816 39.0517 32.1295 45.5889 28.3588C52.1261 24.5881 54.3734 16.2063 50.5982 9.67683C46.8231 3.14736 38.4379 0.902755 31.9007 4.67013Z" fill="#CB5828"/>
                <path d="M133.1 32.9606C131.863 32.9606 130.701 32.3541 129.995 31.3389L129.896 31.1741L115.897 3.59611C115.706 3.27969 115.442 2.9336 114.957 2.9336C114.363 2.9336 113.95 3.3522 113.95 3.79057V31.5564C113.95 32.331 113.323 32.9573 112.548 32.9573C111.772 32.9573 111.146 32.331 111.146 31.5564V3.79387C111.146 1.71077 112.842 0.0166016 114.927 0.0166016C116.165 0.0166016 117.326 0.623074 118.033 1.63826L118.132 1.80635L132.344 29.803C132.529 30.0271 132.806 30.1622 133.1 30.1622C133.638 30.1622 134.077 29.7239 134.077 29.1866V1.41742C134.077 0.64285 134.704 0.0166016 135.479 0.0166016C136.255 0.0166016 136.882 0.64285 136.882 1.41742V29.1833C136.882 31.2664 135.186 32.9606 133.1 32.9606Z" fill="white"/>
                <path d="M92.2437 32.9604C90.0459 32.9604 88.1385 32.5781 86.581 31.8233C85.0135 31.0652 83.7265 30.0336 82.753 28.7547C81.796 27.5022 81.103 26.0453 80.7004 24.4237C80.3143 22.8844 80.1163 21.2463 80.1163 19.5587V1.4173C80.1163 0.642728 80.7433 0.0164795 81.5188 0.0164795C82.2943 0.0164795 82.9213 0.642728 82.9213 1.4173V19.562C82.9213 21.0189 83.0896 22.4296 83.4196 23.748C83.7298 24.9972 84.2578 26.1113 84.9805 27.0605C85.6966 27.9999 86.6206 28.7349 87.8052 29.3084C88.9767 29.8753 90.4716 30.1654 92.2437 30.1654C94.0158 30.1654 95.5073 29.8786 96.6821 29.3084C97.8635 28.7349 98.7875 27.9999 99.5036 27.0605C100.23 26.1113 100.754 24.9972 101.068 23.7513C101.398 22.4296 101.566 21.0189 101.566 19.5653V1.4173C101.566 0.642728 102.193 0.0164795 102.969 0.0164795C103.744 0.0164795 104.371 0.642728 104.371 1.4173V19.562C104.371 21.2463 104.176 22.8811 103.787 24.427C103.381 26.0453 102.691 27.5022 101.734 28.758C100.758 30.0369 99.4706 31.0685 97.9064 31.8266C96.3455 32.5814 94.4415 32.9637 92.2437 32.9637V32.9604Z" fill="white"/>
                <path d="M170.67 32.9601H146.475C144.97 32.9601 143.601 32.1987 142.806 30.9264C142.01 29.6509 141.931 28.0852 142.594 26.7371L154.689 2.44859C155.421 0.958781 156.91 0.0292969 158.573 0.0292969C160.236 0.0292969 161.724 0.955485 162.457 2.44859L174.555 26.7371C175.218 28.0852 175.139 29.6509 174.343 30.9264C173.548 32.1987 172.175 32.9601 170.674 32.9601H170.67ZM157.207 3.68131L145.109 27.9699C144.871 28.4511 144.901 28.9883 145.185 29.4432C145.469 29.8981 145.941 30.1584 146.475 30.1584H170.67C171.208 30.1584 171.677 29.8981 171.961 29.4432C172.245 28.9883 172.271 28.4511 172.037 27.9699L159.939 3.68131C159.678 3.14735 159.167 2.83093 158.573 2.83093C157.979 2.83093 157.467 3.14735 157.207 3.68131Z" fill="#2B76BC"/>
              </g>
              <defs>
                <clipPath id="clip0_827_4">
                  <rect width="175" height="33" fill="white"/>
                </clipPath>
              </defs>
            </svg>
            
            <div className="w-px h-12 bg-white"></div>
            
            <div className="text-white text-2xl font-normal">Maintenace Dashboard</div>
          </div>
          
          {/* Navigation Links and User Section */}
          <div className="flex pl-14 justify-end items-center gap-14">
            <div className="flex items-center gap-14">
              <div className="text-status-blue text-xl font-bold cursor-pointer">Overview</div>
              <div className="text-white text-xl font-light cursor-pointer hover:text-gray-300">Maintenance</div>
              <div className="text-white text-xl font-light cursor-pointer hover:text-gray-300">Map</div>
              <div className="text-white text-xl font-light cursor-pointer hover:text-gray-300">Settings</div>
            </div>
            
            <div className="flex justify-end items-center gap-11">
              <div className="flex justify-end items-center gap-11">
                <div className="w-38 h-9 rounded-md bg-gray-700 flex items-center px-4">
                  <span className="text-white text-base font-bold">Soluna</span>
                  <ChevronDown className="w-4 h-4 text-white ml-auto" />
                </div>
                <User className="w-7 h-7 text-white" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex min-w-full px-12 py-10 flex-col items-center gap-13 bg-dashboard-background">
        {/* Stats Header */}
        <div className="flex p-5 px-8 justify-center items-center gap-3 self-stretch rounded-md bg-dashboard-header">
          <div className="flex h-8 px-12 justify-between items-center flex-1">
            {statsData.map((stat, idx) => (
              <div key={idx} className="flex justify-center items-center gap-4">
                <div className="text-white text-right text-base font-bold">{stat.label}</div>
                <div className="text-white text-2xl font-bold">{stat.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Dashboard Content */}
        <div className="flex pb-14 justify-center items-center gap-12 self-stretch flex-wrap mt-8">
          {/* Left Section - Lists */}
          <div className="grid h-[724px] min-w-[720px] gap-12 flex-1 grid-cols-2">
            {/* Urgent Items */}
            <div className="flex flex-col items-start gap-1 flex-1 col-span-1 justify-center w-full">
              <div className="flex justify-center items-center gap-3 mb-1">
                <h2 className="text-white text-2xl font-bold">Urgent Items</h2>
              </div>
              <div className="flex flex-col gap-0 flex-1 max-h-[645px] overflow-y-auto scrollbar-thin scrollbar-track-black scrollbar-thumb-gray-600 w-full">
                {urgentItems.map((item, idx) => (
                  <MaintenanceItem key={idx} {...item} />
                ))}
              </div>
            </div>

            {/* Upcoming Items */}
            <div className="flex flex-col justify-center items-start gap-1 flex-1 col-span-1">
              <div className="flex justify-between items-center self-stretch mb-1">
                <div className="flex justify-center items-center gap-3">
                  <h2 className="text-white text-2xl font-bold">Upcoming Items</h2>
                </div>
                <div className="w-22 h-9 relative">
                  <div className="w-22 h-9 rounded-md bg-black absolute left-0 top-0"></div>
                  <div className="text-white text-sm font-normal absolute left-1 top-2">3 Month</div>
                  <ChevronDown className="w-2 h-3 text-white absolute right-2 top-3" />
                </div>
              </div>
              <div className="flex flex-col gap-0 flex-1 max-h-[645px] overflow-y-auto scrollbar-thin scrollbar-track-black scrollbar-thumb-gray-600 w-full">
                {upcomingItems.map((item, idx) => (
                  <MaintenanceItem key={idx} {...item} />
                ))}
              </div>
            </div>
          </div>

          {/* Right Section - Equipment Cards */}
          <div className="grid h-[724px] min-w-[784px] gap-11 flex-1 grid-cols-3 grid-rows-2">
            <EquipmentCard 
              name="Dorothy 1A"
              status="In Repair" 
              statusType="warning"
              downtimes={[
                { company: "Bit Digital, Bitmine", datetime: "10/25/2025   08:00 - 16:00" },
                { company: "Compass Mining", datetime: "12/17/2025   08:00 - 16:00" }
              ]}
              equipmentInRepair="D1P2200010"
            />
            
            <EquipmentCard 
              name="Dorothy 1B"
              status="Healthy"
              statusType="healthy"
              downtimes={[
                { company: "Bit Digital, Bitmine", datetime: "10/25/2025   08:00 - 16:00" }
              ]}
            />
            
            <EquipmentCard 
              name="Dorothy 2"
              status="Healthy" 
              statusType="healthy"
            />
            
            <EquipmentCard 
              name="Kati"
              status="Offline"
              statusType="offline"
            />
            
            <EquipmentCard 
              name="Sophie"
              status="Healthy"
              statusType="healthy" 
            />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex min-w-full px-9 py-7 justify-center items-center gap-3 bg-dashboard-header">
        <div className="flex h-11 px-8 justify-between items-center flex-1"></div>
      </div>
    </div>
  );
}
