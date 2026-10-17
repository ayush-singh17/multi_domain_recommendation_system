import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useLocation } from 'react-router-dom';
import Results from './Results';
import API from '../api/axios';

jest.mock('react-router-dom', () => ({ useLocation: jest.fn(), useNavigate: () => jest.fn(), Navigate: () => null }));
jest.mock('../api/axios', () => ({ get: jest.fn(), post: jest.fn() }));
jest.mock('../components/JournalCard', () => ({ journal }) => <article>{journal.title}</article>);
jest.mock('../components/CompareModal', () => () => null);

beforeEach(() => {
  const plans = { A: [], B: [], C: [] };
  for (let index = 0; index < 55; index++) {
    const plan = ['A', 'B', 'C'][index % 3];
    plans[plan].push({ title: `Journal ${String(index + 1).padStart(3, '0')}`, issn: `issn-${index}`, quartile: `Q${index % 3 + 1}`, risk_level: 'Low', final_score: 1 - index / 100, h_index: 100, sjr: 2, homepage_url: 'https://example.org' });
  }
  useLocation.mockReturnValue({ state: { results: { plans, stats: { total: 55 } }, focus: 'General / Best Fit' } });
  API.get.mockResolvedValue({ data: { total: 1, journals: [{ title: 'Outside results', issn: '1234-5678', quartile: 'Q1' }] } });
});

test('orders all plans globally, paginates, and resets pagination after filtering', () => {
  render(<Results />);
  expect(screen.getAllByRole('article')).toHaveLength(10);
  expect(screen.getAllByRole('article')[0]).toHaveTextContent('Journal 001');
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  expect(screen.getAllByRole('article')[0]).toHaveTextContent('Journal 013');
  fireEvent.change(screen.getByLabelText('Per page'), { target: { value: '20' } });
  expect(screen.getAllByRole('article')).toHaveLength(20);
  expect(screen.getAllByRole('article')[0]).toHaveTextContent('Journal 001');
  fireEvent.click(screen.getByRole('button', { name: 'Last' }));
  fireEvent.click(screen.getByRole('button', { name: /^Q1/ }));
  expect(screen.getByLabelText('Page number')).toHaveValue('1');
  expect(screen.getAllByRole('article')).toHaveLength(19);
  expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
});

test('timeline preserves selections across pages/tabs and accepts catalogue journals outside results', async () => {
  render(<Results />);
  fireEvent.click(screen.getAllByRole('button', { name: '+ Add to timeline' })[0]);
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  fireEvent.click(screen.getByRole('button', { name: /^Timeline Calculator/ }));
  expect(screen.getByLabelText('Decision weeks for Journal 001')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Journal name or ISSN'), { target: { value: 'Outside' } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Add', exact: true })).toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'Add', exact: true }));
  expect(screen.getByText('Your sequence (2)')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Decision weeks for Journal 001'), { target: { value: '4' } });
  expect(screen.getByText('week 26')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Move Outside results earlier' }));
  expect(screen.getAllByLabelText(/Decision weeks for/)[0]).toHaveAttribute('aria-label', 'Decision weeks for Outside results');
  fireEvent.click(screen.getByRole('button', { name: /^Results \(/ }));
  expect(screen.getByLabelText('Page number')).toHaveValue('2');
  fireEvent.click(screen.getByRole('button', { name: /^Timeline Calculator/ }));
  expect(screen.getByLabelText('Decision weeks for Journal 001')).toHaveValue(4);
  fireEvent.click(screen.getByRole('button', { name: 'Remove Journal 001' }));
  expect(screen.getByText('Your sequence (1)')).toBeInTheDocument();
});


test('Q3 filter restores all matches and clearing it restores the mixed-list cap', () => {
  render(<Results />);
  expect(screen.getByRole('button', { name: 'Results (39)', exact: true })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /^Q3/ }));
  expect(screen.getByRole('button', { name: 'Results (18)', exact: true })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  expect(screen.getAllByRole('article')).toHaveLength(8);
  fireEvent.click(screen.getByRole('button', { name: /Clear/ }));
  expect(screen.getByRole('button', { name: 'Results (39)', exact: true })).toBeInTheDocument();
  expect(screen.getByLabelText('Page number')).toHaveValue('1');
});
