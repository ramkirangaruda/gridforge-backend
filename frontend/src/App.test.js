import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the GridForge header', () => {
  render(<App />);
  expect(screen.getByText(/gridforge/i)).toBeInTheDocument();
});
