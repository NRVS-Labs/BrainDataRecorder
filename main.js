// Modules
const {app, BrowserWindow, ipcMain} = require('electron')
const path = require('path');

// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
let mainWindow

// Create a new BrowserWindow when `app` is ready
function createWindow () {

  mainWindow = new BrowserWindow({
    width: 1000, 
    height: 800,
    // --- !! IMPORTANT !! ---
    // Disable 'contextIsolation' to allow 'nodeIntegration'
    // 'contextIsolation' defaults to "true" as from Electron v12
    icon: path.join(__dirname, 'assets', 'favicon.ico'),
    contextIsolation: false,
    nodeIntegration: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  })

  // Load index.html into the new BrowserWindow
  mainWindow.loadFile('index.html')

  // Open DevTools - Remove for PRODUCTION!
  // mainWindow.webContents.openDevTools();

  // Listen for window being closed
  mainWindow.on('closed',  () => {
    mainWindow = null
  })
}

// Electron `app` is ready
app.on('ready', createWindow)

// App Logic (Backend)

// Example of updating the banner
setTimeout(() => {
  mainWindow.webContents.send('update-banner', 'New message from the backend!');
}, 5000); // Sends a message after 5 seconds


// Quit when all windows are closed - (Not macOS - Darwin)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// When app icon is clicked and app is running, (macOS) recreate the BrowserWindow
app.on('activate', () => {
  if (mainWindow === null) createWindow()
})
