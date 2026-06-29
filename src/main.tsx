import React from 'react';
import { createRoot } from 'react-dom/client';
import { routeTree } from './routeTree.gen';
import { createRouter, RouterProvider, createBrowserHistory } from '@tanstack/react-router';
import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient();

const router = createRouter({
  routeTree,
  history: createBrowserHistory(),
  context: { queryClient },
});

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

createRoot(rootElement).render(
  <RouterProvider router={router} />
);
