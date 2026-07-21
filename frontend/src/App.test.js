import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import * as api from './api';

// Auto-mocks every export as jest.fn(); each test below sets return
// values for the ones it actually exercises. Also sidesteps jsdom not
// implementing EventSource: Dashboard only calls `new EventSource(...)`
// when getTaskStreamUrl() returns a truthy value (see its guard clause),
// so leaving that mocked to null keeps a successful-login test from
// crashing on a browser API jsdom doesn't have.
jest.mock('./api');

beforeEach(() => {
  jest.clearAllMocks();
  api.getTaskStreamUrl.mockReturnValue(null);
});

test('renders the GridForge header', () => {
  api.isAuthenticated.mockReturnValue(false);
  render(<App />);
  expect(screen.getByText(/gridforge/i)).toBeInTheDocument();
});

test('shows the Login form, not the dashboard, when logged out', () => {
  api.isAuthenticated.mockReturnValue(false);
  render(<App />);
  expect(screen.getByRole('heading', { name: /log in/i })).toBeInTheDocument();
  expect(screen.queryByText(/submit new project/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/task dashboard/i)).not.toBeInTheDocument();
});

test('switches between Login and Register views', async () => {
  api.isAuthenticated.mockReturnValue(false);
  render(<App />);

  await userEvent.click(screen.getByRole('button', { name: /register/i }));
  expect(screen.getByRole('heading', { name: /create an account/i })).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: /log in/i }));
  expect(screen.getByRole('heading', { name: /log in/i })).toBeInTheDocument();
});

test('successful login reveals the dashboard and submit form', async () => {
  api.isAuthenticated.mockReturnValue(false);
  api.login.mockResolvedValue({ access_token: 'fake-token', token_type: 'bearer' });
  render(<App />);

  await userEvent.type(screen.getByLabelText(/username/i), 'alice');
  await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');
  await userEvent.click(screen.getByRole('button', { name: /^log in$/i }));

  await waitFor(() => {
    expect(screen.getByText(/submit new project/i)).toBeInTheDocument();
  });
  expect(api.login).toHaveBeenCalledWith('alice', 'password123');
});

test('a 401 from login shows "incorrect username or password", not a generic error', async () => {
  api.isAuthenticated.mockReturnValue(false);
  const err = new Error('Incorrect username or password');
  err.status = 401;
  api.login.mockRejectedValue(err);
  render(<App />);

  await userEvent.type(screen.getByLabelText(/username/i), 'alice');
  await userEvent.type(screen.getByLabelText(/^password$/i), 'wrong');
  await userEvent.click(screen.getByRole('button', { name: /^log in$/i }));

  await waitFor(() => {
    expect(screen.getByText(/incorrect username or password/i)).toBeInTheDocument();
  });
  // Still on the login form, not bounced anywhere else.
  expect(screen.getByRole('heading', { name: /log in/i })).toBeInTheDocument();
});

test('a network failure (no status) during login shows a distinct message', async () => {
  api.isAuthenticated.mockReturnValue(false);
  const err = new Error('Network Error');
  err.status = null;
  api.login.mockRejectedValue(err);
  render(<App />);

  await userEvent.type(screen.getByLabelText(/username/i), 'alice');
  await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');
  await userEvent.click(screen.getByRole('button', { name: /^log in$/i }));

  await waitFor(() => {
    expect(screen.getByText(/can't reach the server/i)).toBeInTheDocument();
  });
});

test('registering redirects to Login with a confirmation notice, not auto-login', async () => {
  api.isAuthenticated.mockReturnValue(false);
  api.register.mockResolvedValue({ message: 'User registered successfully.' });
  render(<App />);

  // The "Register" link (Login view) and the "Register" submit button
  // (Register view) never coexist, so this selector is unambiguous both
  // before and after the view switches.
  await userEvent.click(screen.getByRole('button', { name: /^register$/i }));
  await userEvent.type(screen.getByLabelText(/username/i), 'alice');
  await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');
  await userEvent.type(screen.getByLabelText(/confirm password/i), 'password123');
  await userEvent.click(screen.getByRole('button', { name: /^register$/i }));

  await waitFor(() => {
    expect(screen.getByRole('heading', { name: /log in/i })).toBeInTheDocument();
  });
  expect(screen.getByText(/account created.*please log in/i)).toBeInTheDocument();
  expect(api.login).not.toHaveBeenCalled();
});

test('logging out returns to the Login view', async () => {
  api.isAuthenticated.mockReturnValue(true);
  render(<App />);

  expect(screen.getByText(/submit new project/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /log out/i }));

  expect(api.logout).toHaveBeenCalled();
  expect(screen.getByRole('heading', { name: /log in/i })).toBeInTheDocument();
});

test('an app-wide auth-expired event bounces back to Login with a session-expired notice', async () => {
  api.isAuthenticated.mockReturnValue(true);
  render(<App />);
  expect(screen.getByText(/submit new project/i)).toBeInTheDocument();

  act(() => {
    window.dispatchEvent(new Event(api.AUTH_EXPIRED_EVENT));
  });

  await waitFor(() => {
    expect(screen.getByRole('heading', { name: /log in/i })).toBeInTheDocument();
  });
  expect(screen.getByText(/session expired/i)).toBeInTheDocument();
});
