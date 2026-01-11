import express from 'express';
import { runAudit } from '../services/audit';

const router = express.Router();

router.post('/run', async (req, res) => {
  const { sourceCode, contractName } = req.body;
  console.log(`Running audit for contract: ${contractName}`);
  if (!sourceCode || !contractName) {
    console.log('Audit request missing sourceCode or contractName');
    return res.status(400).json({ error: 'sourceCode and contractName required' });
  }

  const result = await runAudit(sourceCode, contractName);
  console.log(`Audit completed for ${contractName}`);
  res.json(result);
});

export default router;