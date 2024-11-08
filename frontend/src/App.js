import React, { useState, useEffect } from 'react';
import axios from 'axios';
import invlogo from './assets/BDR-inverted.png'

function App() {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [buttonColor, setButtonColor] = useState('#007bff') // Default blue color
  const [buttonHoverColor, setButtonHoverColor] = useState('#0056b3');
  const [isHovered, setIsHovered] = useState(false); // State for hover effect
  const [time, setTime] = useState(0); // Time in milliseconds
  const [bannerMessage, setBannerMessage] = useState(''); // State for the banner message

  useEffect(() => {
    document.title = 'BDR: Brain Data Recorder';
  }, []);

  useEffect(() => {
    axios.get('http://localhost:5000/serial-devices')
      .then(response => {
        console.log('Fetched devices:', response);
        setDevices(response.data);
        fetchBannerMessage();
      })
      .catch(error => {
        console.error('Error fetching serial devices:', error);
      });
  }, []);

  useEffect(() => {
    let intervalId;
    if (isRecording) {
      intervalId = setInterval(() => {
        setTime(prevTime => prevTime + 100);
      }, 100);
    }
    return () => clearInterval(intervalId);
  }, [isRecording, time]);

  const changeButtonColor = () => {
    setButtonColor(prevColor =>
        prevColor === '#007bff' ? '#9e0000' : '#007bff'
      );
    setButtonHoverColor(prevHoverColor =>
        prevHoverColor === '#0056b3' ? '#720000' : '#0056b3'
      )
  }

  const handleDeviceChange = (event) => {
    setSelectedDevice(event.target.value);
    fetchBannerMessage();
  };

  const handleStartButtonClick = () => {

    if (!isRecording){
      axios.post('http://localhost:5000/start-device')
      .then(response => {
        console.log('[start-device] Status:', response);
      })
      .catch(error => {
        console.error('Error starting stream:', error);
      });
    } else {
      
      axios.post('http://localhost:5000/stop-device')
      .then(response => {

        setTimeout(() => {
          console.log('[stop-device] Status:', response);
        
        }, 1500);

        fetchBannerMessage();

        
      })
      .catch(error => {
        console.error('Error stopping stream:', error);
      });
    }

    setIsRecording(!isRecording);
    changeButtonColor();
    fetchBannerMessage();
  };

  const handleResetButtonClick = () => {
    setTime(0);
    updateBannerMessage("Press START to stream data");
    fetchBannerMessage();
  }

  const formatTime = (ms) => {
    const hours = Math.floor(ms / 3600000);
    const minutes = Math.floor((ms % 3600000) / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    const milliseconds = ms % 1000;

    if (ms % 5000 === 0) {
      fetchBannerMessage();
    }

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}:${String(Math.floor(milliseconds / 10)).padStart(2, '0')}`;
  };

  
  const fetchBannerMessage = () => {
    axios.get('http://localhost:5000/banner-message')
      .then(response => {
        setBannerMessage(response.data.message);
      })
      .catch(error => {
        console.error('Error fetching banner message:', error);
      });
  };
  
  const updateBannerMessage = (message) => {
    axios.post('http://localhost:5000/banner-message', { message })
      .then(response => {
        setBannerMessage(response.data.new_message);
      })
      .catch(error => {
        console.error('Error updating banner message:', error);
      });
  };

  return (
    <div class="container">
      <img src={invlogo} alt="BDR: Brain Data Recorder" class="title-image"></img>
      <div class="content">
        <button onClick={handleStartButtonClick} 
          class="circular-button" 
          onMouseEnter={() => setIsHovered(true)} // override since CSS isnt working due to buttonColor state
          onMouseLeave={() => setIsHovered(false)}
          style={{ backgroundColor: isHovered ? buttonHoverColor : buttonColor }}>
          {isRecording ? 'Stop' : 'Start'}
        </button>
        <button onClick={handleResetButtonClick} class="circular-button-reset"> 
          Reset
        </button>
        <div>
          <select class="dropdown" value={selectedDevice} onChange={handleDeviceChange}>
            <option value="" disabled>Select a device</option>
            {devices.map(device => (
              <option key={device.id} value={device.id}>
                {device.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <h2 class="timer">{formatTime(time)}</h2>
      </div>
      <Banner message={bannerMessage}/>
    </div>
  );

  function Banner({ message }) {
    return (
      <div className="banner">
        <p>{message}</p>
      </div>
    );
  }

}

export default App;
