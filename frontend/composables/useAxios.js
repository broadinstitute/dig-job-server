import axios from 'axios';

export default function (config) {
  const configuredAxios = axios.create({
    baseURL: config.public.apiBaseUrl,
    headers: {
      "Content-Type": "application/json",
    },
  });
  configuredAxios.interceptors.request.use(config => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // An expired token otherwise reaches the caller as a bare AxiosError, and
  // pages render an empty state instead of asking the user to log in -- the
  // datasets list shows a signed-in header above an empty table, which reads as
  // "my data is gone". Handle it once here so every call site behaves the same.
  //
  // Only a real 401 counts. A gateway error (upstream down) arrives with NO
  // response at all and must not be mistaken for a session problem.
  configuredAxios.interceptors.response.use(
    response => response,
    error => {
      const onLoginPage =
        typeof window !== 'undefined' &&
        window.location.pathname.startsWith('/login');
      if (error.response?.status === 401 && !onLoginPage) {
        localStorage.removeItem('authToken');
        const redirect = window.location.pathname + window.location.search;
        window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`);
      }
      return Promise.reject(error);
    },
  );

  return configuredAxios;
}
