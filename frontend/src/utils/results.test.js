import { capDefaultMix, filterJournals } from './results';

test('caps Q3 and Q4 independently across the whole sorted list, preserving Q1/Q2', () => {
  const journals = Array.from({ length: 24 }, (_, i) => ({ title: `Journal ${i}`, quartile: `Q${i % 4 + 1}`, final_score: 1 - i / 100 }));
  const mixed = capDefaultMix(journals);
  expect(mixed.filter(j => j.quartile === 'Q1')).toHaveLength(6);
  expect(mixed.filter(j => j.quartile === 'Q2')).toHaveLength(6);
  expect(mixed.filter(j => j.quartile === 'Q3').map(j => j.title)).toEqual(['Journal 2', 'Journal 6']);
  expect(mixed.filter(j => j.quartile === 'Q4').map(j => j.title)).toEqual(['Journal 3', 'Journal 7']);
  expect(filterJournals(journals, 0, 0, 'Q3')).toHaveLength(6);
  expect(filterJournals(journals, 0, 0, 'Q4')).toHaveLength(6);
  expect(mixed.map(j => j.final_score)).toEqual(mixed.map(j => j.final_score).sort((a, b) => b - a));
});
