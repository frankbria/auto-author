import React from 'react';
import { render, screen } from '@testing-library/react';

function Hello() {
  return <h1>Hello, world!</h1>;
}

test('renders hello text', () => {
  render(<Hello />);
  expect(screen.getByText(/hello/i)).toBeInTheDocument();
});
