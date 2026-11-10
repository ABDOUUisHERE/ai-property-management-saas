import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, expect, it, vi } from 'vitest';
import { App } from './App';
import { createQueryClient } from '../shared/api/client';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }))));
});

function renderApp() {
  const client = createQueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

it('renders the actual empty state and connection status', async () => {
  renderApp();
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Bienvenue chez vous');
  expect(await screen.findByText('Connexion au service établie.')).toBeInTheDocument();
  expect(screen.getByText(/L’accès aux comptes/)).toBeInTheDocument();
});

it('supports keyboard navigation and moves focus after a route change', async () => {
  renderApp();
  const user = userEvent.setup();
  await user.tab();
  expect(screen.getByText('Aller au contenu')).toHaveFocus();
  await user.click(screen.getByRole('link', { name: 'Guide de bienvenue' }));
  await waitFor(() => expect(screen.getByRole('main')).toHaveFocus());
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Un lieu pour tout réunir');
});

it('traps dialog focus, closes with Escape and returns focus', async () => {
  renderApp();
  const user = userEvent.setup();
  const trigger = screen.getByRole('button', { name: 'À propos' });
  await user.click(trigger);
  const dialog = screen.getByRole('dialog', { name: 'Property Management' });
  expect(dialog).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Fermer' })).toHaveFocus();
  await user.keyboard('{Escape}');
  await waitFor(() => expect(trigger).toHaveFocus());
});

it('offers a retry after a service failure', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network failure')));
  renderApp();
  expect(await screen.findByRole('button', { name: 'Réessayer' })).toBeInTheDocument();
});
