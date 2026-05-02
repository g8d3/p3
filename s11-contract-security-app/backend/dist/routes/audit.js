"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const audit_1 = require("../services/audit");
const router = express_1.default.Router();
router.post('/run', async (req, res) => {
    const { sourceCode, contractName } = req.body;
    console.log(`Running audit for contract: ${contractName}`);
    if (!sourceCode || !contractName) {
        console.log('Audit request missing sourceCode or contractName');
        return res.status(400).json({ error: 'sourceCode and contractName required' });
    }
    const result = await (0, audit_1.runAudit)(sourceCode, contractName);
    console.log(`Audit completed for ${contractName}`);
    res.json(result);
});
exports.default = router;
