import '@mdi/font/css/materialdesignicons.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'

import { createApp } from 'vue'
import VueApexCharts from 'vue3-apexcharts'
import { createVuetify } from 'vuetify'
import 'vuetify/styles'

import App from './App.vue'

const vuetify = createVuetify({
  icons: {
    defaultSet: 'mdi',
  },
  theme: {
    defaultTheme: 'cowboyDark',
    themes: {
      cowboyDark: {
        dark: true,
        colors: {
          background: '#111714',
          surface: '#19211d',
          primary: '#69c3a5',
          secondary: '#ff866b',
          accent: '#89b6d0',
          error: '#ff8b7f',
          info: '#89b6d0',
          success: '#69c3a5',
          warning: '#f0ba62',
        },
      },
    },
  },
})

createApp(App).use(vuetify).use(VueApexCharts).mount('#app')
