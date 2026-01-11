"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const protection_1 = require("../services/protection");
const router = express_1.default.Router();
router.post('/start/:address', (req, res) => {
    const { address } = req.params;
    console.log(`Starting protection monitoring for address: ${address}`);
    protection_1.protector.startMonitoring(address);
    console.log(`Protection monitoring started for ${address}`);
    res.json({ message: `Monitoring started for ${address}` });
});
router.post('/stop/:address', (req, res) => {
    const { address } = req.params;
    console.log(`Stopping protection monitoring for address: ${address}`);
    protection_1.protector.stopMonitoring(address);
    console.log(`Protection monitoring stopped for ${address}`);
    res.json({ message: `Monitoring stopped for ${address}` });
});
router.get('/alerts', (req, res) => {
    console.log('Fetching protection alerts');
    const alerts = protection_1.protector.getAlerts();
    console.log(`Fetched ${alerts.length} alerts`);
    res.json(alerts);
});
exports.default = router;
