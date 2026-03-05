import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import invlogo from './assets/BDR-inverted.png';

const API = 'http://localhost:5000';

function App() {
  // Device state
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [serialPort, setSerialPort] = useState('');
  const [requiresSerial, setRequiresSerial] = useState(false);

  // Board state
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [boardInfo, setBoardInfo] = useState(null);

  // Timer
  const [time, setTime] = useState(0);
  const timerRef = useRef(null);

  // UDP state
  const [udpEnabled, setUdpEnabled] = useState(false);
  const [udpIp, setUdpIp] = useState('127.0.0.1');
  const [udpPort, setUdpPort] = useState('12345');
  const [udpStreaming, setUdpStreaming] = useState(false);
  const [showUdpPanel, setShowUdpPanel] = useState(false);

  // UI state
  const [bannerMessage, setBannerMessage] = useState('');
  const [bannerType, setBannerType] = useState('info'); // 'info', 'success', 'error'
  const [isLoading, setIsLoading] = useState(false);

  // ---- Page title ----
  useEffect(() => {
    document.title = 'BDR: Brain Data Recorder';
  }, []);

  // ---- Fetch devices on mount ----
  useEffect(() => {
    axios.get(`${API}/devices`)
      .then(res => {
        setDevices(res.data);
        fetchBannerMessage();
      })
      .catch(err => {
        console.error('Error fetching devices:', err);
        showBanner('Could not reach backend. Is the Flask server running?', 'error');
      });
  }, []);

  // ---- Timer ----
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setTime(prev => prev + 100);
      }, 100);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  // ---- Poll banner while recording ----
  useEffect(() => {
    if (!isRecording) return;
    const id = setInterval(fetchBannerMessage, 5000);
    return () => clearInterval(id);
  }, [isRecording]);

  // ---- Helpers ----
  const showBanner = (msg, type = 'info') => {
    setBannerMessage(msg);
    setBannerType(type);
  };

  const fetchBannerMessage = useCallback(() => {
    axios.get(`${API}/banner-message`)
      .then(res => setBannerMessage(res.data.message))
      .catch(() => {});
  }, []);

  const formatTime = (ms) => {
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    const cs = Math.floor((ms % 1000) / 10);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(cs).padStart(2, '0')}`;
  };

  // ---- Device selection ----
  const handleDeviceChange = (e) => {
    const deviceId = e.target.value;
    setSelectedDeviceId(deviceId);

    const device = devices.find(d => d.id === deviceId);
    if (device) {
      setRequiresSerial(device.requires_serial || false);
      if (device.serial_port) {
        setSerialPort(device.serial_port);
      } else {
        setSerialPort('');
      }
    }

    // Disconnect if currently connected to a different device
    if (isConnected) {
      handleDisconnect();
    }
  };

  // ---- Connect / Disconnect ----
  const handleConnect = async () => {
    if (!selectedDeviceId) {
      showBanner('Please select a device first.', 'error');
      return;
    }
    setIsLoading(true);
    try {
      let boardId;
      let port = null;

      if (selectedDeviceId.startsWith('serial:')) {
        // A raw serial port was selected — default to Cyton (board 0)
        boardId = 0;
        port = selectedDeviceId.replace('serial:', '');
      } else {
        boardId = parseInt(selectedDeviceId, 10);
        port = serialPort || null;
      }

      const res = await axios.post(`${API}/connect-device`, {
        board_id: boardId,
        serial_port: port,
      });

      if (res.data.success) {
        setIsConnected(true);
        setBoardInfo(res.data.data || null);
        showBanner(res.data.message, 'success');
      } else {
        showBanner(res.data.message, 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.message || err.message;
      showBanner(`Connection failed: ${msg}`, 'error');
    }
    setIsLoading(false);
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      if (isRecording) {
        await handleStop();
      }
      await axios.post(`${API}/disconnect-device`);
      setIsConnected(false);
      setBoardInfo(null);
      showBanner('Device disconnected.', 'info');
    } catch (err) {
      console.error('Disconnect error:', err);
    }
    setIsLoading(false);
  };

  // ---- Start / Stop recording ----
  const handleStart = async () => {
    setIsLoading(true);
    try {
      // Auto-connect if not already connected
      if (!isConnected) {
        await handleConnect();
      }

      const res = await axios.post(`${API}/start-device`);
      if (res.data.success) {
        setIsRecording(true);
        setTime(0);
        showBanner(res.data.message, 'success');

        // Start UDP if enabled
        if (udpEnabled) {
          await startUdp();
        }
      } else {
        showBanner(res.data.message, 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.message || err.message;
      showBanner(`Start failed: ${msg}`, 'error');
    }
    setIsLoading(false);
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      // Stop UDP first
      if (udpStreaming) {
        await stopUdp();
      }

      const res = await axios.post(`${API}/stop-device`);
      setIsRecording(false);

      if (res.data.success) {
        const filename = res.data.data?.filename;
        showBanner(
          filename ? `Saved: ${filename}` : res.data.message,
          'success'
        );
      } else {
        showBanner(res.data.message, 'error');
      }
    } catch (err) {
      setIsRecording(false);
      const msg = err.response?.data?.message || err.message;
      showBanner(`Stop error: ${msg}`, 'error');
    }
    setIsLoading(false);
  };

  const handleRecordToggle = () => {
    if (isRecording) {
      handleStop();
    } else {
      handleStart();
    }
  };

  const handleReset = () => {
    setTime(0);
    showBanner('Timer reset. Press Start to record.', 'info');
  };

  // ---- UDP ----
  const configureUdp = async () => {
    try {
      await axios.post(`${API}/udp/configure`, {
        ip: udpIp,
        port: parseInt(udpPort, 10),
      });
    } catch (err) {
      console.error('UDP configure error:', err);
    }
  };

  const startUdp = async () => {
    try {
      await configureUdp();
      const res = await axios.post(`${API}/udp/start`);
      if (res.data.success) {
        setUdpStreaming(true);
      }
    } catch (err) {
      console.error('UDP start error:', err);
    }
  };

  const stopUdp = async () => {
    try {
      await axios.post(`${API}/udp/stop`);
      setUdpStreaming(false);
    } catch (err) {
      console.error('UDP stop error:', err);
    }
  };

  // ---- Render helpers ----
  const bannerClass = `banner banner-${bannerType}`;

  const selectedDevice = devices.find(d => d.id === selectedDeviceId);
  const selectedLabel = selectedDevice ? selectedDevice.label : '';

  return (
    <div className="app-container">
      {/* Logo */}
      <img src={invlogo} alt="BDR: Brain Data Recorder" className="title-image" />

      {/* Connection status indicator */}
      <div className="status-row">
        <span className={`status-dot ${isConnected ? (isRecording ? 'recording' : 'connected') : ''}`} />
        <span className="status-text">
          {isRecording
            ? `Recording — ${selectedLabel}`
            : isConnected
              ? `Connected — ${selectedLabel}`
              : 'No device connected'}
        </span>
      </div>

      {/* Device selector */}
      <div className="device-section">
        <select
          className="dropdown"
          value={selectedDeviceId}
          onChange={handleDeviceChange}
          disabled={isRecording}
        >
          <option value="" disabled>Select a device</option>
          {devices.map(device => (
            <option key={device.id} value={device.id}>
              {device.label}
            </option>
          ))}
        </select>

        {/* Serial port input for boards that need it */}
        {requiresSerial && (
          <input
            className="serial-input"
            type="text"
            placeholder="Serial port (e.g. COM3)"
            value={serialPort}
            onChange={e => setSerialPort(e.target.value)}
            disabled={isConnected}
          />
        )}

        {/* Connect / Disconnect button */}
        <button
          className={`btn btn-connect ${isConnected ? 'btn-disconnect' : ''}`}
          onClick={isConnected ? handleDisconnect : handleConnect}
          disabled={isLoading || isRecording || (!isConnected && !selectedDeviceId)}
        >
          {isConnected ? 'Disconnect' : 'Connect'}
        </button>
      </div>

      {/* Board info */}
      {boardInfo && (
        <div className="board-info">
          <span>Sampling rate: {boardInfo.sampling_rate || '—'} Hz</span>
          <span className="separator">•</span>
          <span>EEG channels: {boardInfo.num_eeg_channels || '—'}</span>
        </div>
      )}

      {/* Controls */}
      <div className="controls">
        <button
          className={`btn-circular ${isRecording ? 'btn-stop' : 'btn-start'}`}
          onClick={handleRecordToggle}
          disabled={isLoading || (!isConnected && !selectedDeviceId)}
          title={isRecording ? 'Stop recording' : 'Start recording'}
        >
          {isRecording ? 'Stop' : 'Start'}
        </button>

        <button
          className="btn-circular btn-reset"
          onClick={handleReset}
          disabled={isRecording}
          title="Reset timer"
        >
          Reset
        </button>
      </div>

      {/* Timer */}
      <div className="timer">{formatTime(time)}</div>

      {/* UDP Toggle */}
      <div className="udp-section">
        <button
          className={`btn btn-udp-toggle ${showUdpPanel ? 'active' : ''}`}
          onClick={() => setShowUdpPanel(!showUdpPanel)}
        >
          UDP Streaming {udpStreaming ? '🟢' : ''}
        </button>

        {showUdpPanel && (
          <div className="udp-panel">
            <div className="udp-row">
              <label>
                <input
                  type="checkbox"
                  checked={udpEnabled}
                  onChange={e => setUdpEnabled(e.target.checked)}
                  disabled={isRecording}
                />
                Enable UDP on record
              </label>
            </div>
            <div className="udp-row">
              <input
                className="udp-input"
                type="text"
                placeholder="IP Address"
                value={udpIp}
                onChange={e => setUdpIp(e.target.value)}
                disabled={udpStreaming}
              />
              <input
                className="udp-input udp-port"
                type="number"
                placeholder="Port"
                value={udpPort}
                onChange={e => setUdpPort(e.target.value)}
                disabled={udpStreaming}
              />
            </div>
            {isRecording && (
              <div className="udp-row">
                <button
                  className={`btn ${udpStreaming ? 'btn-disconnect' : 'btn-connect'}`}
                  onClick={udpStreaming ? stopUdp : startUdp}
                >
                  {udpStreaming ? 'Stop UDP' : 'Start UDP'}
                </button>
              </div>
            )}
            {udpStreaming && (
              <div className="udp-status">
                Streaming to {udpIp}:{udpPort}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Banner */}
      <div className={bannerClass}>
        <p>{bannerMessage}</p>
      </div>
    </div>
  );
}

export default App;