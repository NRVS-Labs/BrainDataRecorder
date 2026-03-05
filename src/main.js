const { app, BrowserWindow } = require('electron');
const path = require('node:path');
const { spawn } = require('child_process');

let backendProcess = null;

function getBackendPath() {
  const isProd = app.isPackaged;
  const platform = process.platform;
  const ext = platform === 'win32' ? '.exe' : '';
  const name = `bdr-backend${ext}`;

  if (isProd) {
    // In packaged app, extraResource copies ./backend/dist -> resources/dist/
    return path.join(process.resourcesPath, 'dist', name);
  } else {
    // In development, use the PyInstaller output
    return path.join(__dirname, '..', 'backend', 'dist', name);
  }
}

function startBackend() {
  const backendPath = getBackendPath();
  console.log(`Starting backend: ${backendPath}`);

  backendProcess = spawn(backendPath, [], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, FLASK_ENV: 'production' },
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`[backend] exited with code ${code}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 800,
    title: 'BDR: Brain Data Recorder',
    icon: './src/images/icon.png',
    // show: true, // do not show until frontend is done loading
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // In production, load the built React files; in dev, load the dev server
  if (app.isPackaged) {
    win.loadFile(path.join(__dirname, '..', 'frontend', 'build', 'index.html'));
  } else {
    win.loadURL('http://localhost:3000');
  }
}

app.whenReady().then(() => {
  startBackend();

  // Give Flask a moment to start before loading the window
  setTimeout(createWindow, 1500);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});