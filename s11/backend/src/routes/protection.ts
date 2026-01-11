import express from 'express';
import { protector } from '../services/protection';

const router = express.Router();

router.post('/start/:address', (req, res) => {
  const { address } = req.params;
  console.log(`Starting protection monitoring for address: ${address}`);
  protector.startMonitoring(address);
  console.log(`Protection monitoring started for ${address}`);
  res.json({ message: `Monitoring started for ${address}` });
});

router.post('/stop/:address', (req, res) => {
  const { address } = req.params;
  console.log(`Stopping protection monitoring for address: ${address}`);
  protector.stopMonitoring(address);
  console.log(`Protection monitoring stopped for ${address}`);
  res.json({ message: `Monitoring stopped for ${address}` });
});

router.get('/alerts', (req, res) => {
  console.log('Fetching protection alerts');
  const alerts = protector.getAlerts();
  console.log(`Fetched ${alerts.length} alerts`);
  res.json(alerts);
});

export default router;