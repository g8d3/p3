import express from 'express';
import { getContractInfo, getSecurityDatasets } from '../services/dataGathering';

const router = express.Router();

router.get('/contract/:address', async (req, res) => {
  const { address } = req.params;
  console.log(`Fetching contract info for address: ${address}`);
  const info = await getContractInfo(address);
  if (info) {
    console.log(`Contract info found for ${address}`);
    res.json(info);
  } else {
    console.log(`Contract not found for ${address}`);
    res.status(404).json({ error: 'Contract not found or verified' });
  }
});

router.get('/datasets', async (req, res) => {
  const datasets = await getSecurityDatasets();
  res.json(datasets);
});

export default router;