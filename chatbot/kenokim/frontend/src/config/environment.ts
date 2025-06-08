import { EnvironmentConfig } from '../types';

interface Config {
  development: EnvironmentConfig;
  production: EnvironmentConfig;
}

const config: Config = {
  development: {
    API_BASE_URL: 'http://localhost:8000'
  },
  production: {
    API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'https://your-api-domain.com'
  }
};

const environment = (process.env.NODE_ENV || 'development') as keyof Config;

export default config[environment]; 