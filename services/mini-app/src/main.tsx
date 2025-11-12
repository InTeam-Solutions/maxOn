import React from 'react';
import ReactDOM from 'react-dom/client';
import '@maxhub/max-ui/dist/styles.css';
import './styles/globals.css';
import { App } from './App';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';

dayjs.locale('ru');

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
