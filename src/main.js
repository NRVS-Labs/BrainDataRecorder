const { app, BrowserWindow } = require('electron');
const path = require('node:path');

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 650,
    title: 'Loading...',
    icon: './src/images/icon.png',
    // show: true, // do not show until frontend is done loading
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });

  win.loadURL('http://localhost:3000'); // React app

  // Wait until the React frontend is ready to load
  // win.webContents.once('did-finish-load', () => {
  //   // Now that frontend is loaded, replace the loading screen

  // });


}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
