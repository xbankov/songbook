import { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.songbook.app',
  appName: 'Songbook',
  webDir: 'dist',
  server: {
    url: process.env.VITE_API_URL || 'http://localhost:8000',
    cleartext: true,
  },
  android: {
    allowMixedContent: true,
  },
}

export default config
