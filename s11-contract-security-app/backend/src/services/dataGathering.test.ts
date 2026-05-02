import { getSecurityDatasets } from './dataGathering';

describe('Data Gathering Service', () => {
  test('should return security datasets', async () => {
    const datasets = await getSecurityDatasets();
    expect(datasets).toBeInstanceOf(Array);
    expect(datasets.length).toBeGreaterThan(0);
  });
});