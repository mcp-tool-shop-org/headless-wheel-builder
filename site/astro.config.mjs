// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  site: 'https://mcp-tool-shop-org.github.io',
  base: '/headless-wheel-builder',
  integrations: [
    starlight({
      title: 'Headless Wheel Builder',
      description: 'Headless Wheel Builder handbook',
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/mcp-tool-shop-org/headless-wheel-builder' }],
      sidebar: [{ label: 'Handbook', autogenerate: { directory: 'handbook' } }],
      customCss: ['./src/styles/starlight-custom.css'],
      disable404Route: true,
    }),
  ],
  vite: { plugins: [tailwindcss()] },
});
