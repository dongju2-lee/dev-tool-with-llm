import type { Meta, StoryObj } from '@storybook/react';
import { Card } from './index';

const meta: Meta<typeof Card> = {
  title: 'Molecules/Card',
  component: Card,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = {
  args: {
    title: 'Card Title',
    subtitle: 'Card Subtitle',
    children: 'This is the card content',
  },
};

export const WithoutTitle: Story = {
  args: {
    children: 'Card without title',
  },
};

export const Hoverable: Story = {
  args: {
    title: 'Hoverable Card',
    subtitle: 'Try hovering over me!',
    children: 'This card has a hover effect',
    hoverable: true,
  },
};

export const Clickable: Story = {
  args: {
    title: 'Clickable Card',
    children: 'Click me!',
    hoverable: true,
    onClick: () => alert('Card clicked!'),
  },
}; 