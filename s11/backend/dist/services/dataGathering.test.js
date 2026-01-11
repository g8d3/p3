"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const dataGathering_1 = require("./dataGathering");
describe('Data Gathering Service', () => {
    test('should return security datasets', async () => {
        const datasets = await (0, dataGathering_1.getSecurityDatasets)();
        expect(datasets).toBeInstanceOf(Array);
        expect(datasets.length).toBeGreaterThan(0);
    });
});
