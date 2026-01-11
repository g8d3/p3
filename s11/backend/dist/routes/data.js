"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const dataGathering_1 = require("../services/dataGathering");
const router = express_1.default.Router();
router.get('/contract/:address', async (req, res) => {
    const { address } = req.params;
    console.log(`Fetching contract info for address: ${address}`);
    const info = await (0, dataGathering_1.getContractInfo)(address);
    if (info) {
        console.log(`Contract info found for ${address}`);
        res.json(info);
    }
    else {
        console.log(`Contract not found for ${address}`);
        res.status(404).json({ error: 'Contract not found or verified' });
    }
});
router.get('/datasets', async (req, res) => {
    const datasets = await (0, dataGathering_1.getSecurityDatasets)();
    res.json(datasets);
});
exports.default = router;
