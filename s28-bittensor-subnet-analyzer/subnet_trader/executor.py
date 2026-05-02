"""Transaction execution with dry-run support."""

import json
from subnet_trader.models import RebalanceOrder
from subnet_trader.config import Config


class Executor:
    """Execute stake/unstake orders on Bittensor.

    Supports dry-run mode (default) that logs actions without
    sending transactions. Switching to live is just DRY_RUN=false.
    """

    def __init__(self, config: Config, wallet_name: str | None = None, hotkey: str | None = None):
        self.config = config
        self.wallet_name = wallet_name
        self.hotkey = hotkey
        self._wallet = None

    def _get_wallet(self):
        """Load wallet for live execution."""
        if self._wallet is None:
            try:
                import bittensor as bt
                self._wallet = bt.wallet(name=self.wallet_name, hotkey=self.hotkey)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load wallet: {e}. "
                    "Set DRY_RUN=true or provide valid wallet credentials."
                )
        return self._wallet

    def execute(self, orders: list[RebalanceOrder]) -> list[dict]:
        """Execute a list of rebalance orders.

        Args:
            orders: List of RebalanceOrder to execute

        Returns:
            List of execution results with status and details
        """
        results = []

        for order in orders:
            if self.config.dry_run:
                result = self._dry_run(order)
            else:
                result = self._execute_live(order)
            results.append(result)

        return results

    def _dry_run(self, order: RebalanceOrder) -> dict:
        """Simulate execution without sending transactions."""
        return {
            "action": order.action,
            "netuid": order.netuid,
            "amount_tao": order.amount_tao,
            "status": "dry_run",
            "message": f"[DRY RUN] Would {order.action} {order.amount_tao:.4f} TAO on subnet {order.netuid}",
            "tx_hash": None,
        }

    def _execute_live(self, order: RebalanceOrder) -> dict:
        """Execute a real transaction on-chain."""
        try:
            import bittensor as bt

            wallet = self._get_wallet()
            subtensor = bt.subtensor(network=self.config.network)

            if order.action == "stake":
                result = subtensor.add_stake(
                    wallet=wallet,
                    netuid=order.netuid,
                    amount=bt.Balance.from_tao(order.amount_tao),
                )
            elif order.action == "unstake":
                result = subtensor.unstake(
                    wallet=wallet,
                    netuid=order.netuid,
                    amount=bt.Balance.from_tao(order.amount_tao),
                )
            else:
                return {
                    "action": order.action,
                    "netuid": order.netuid,
                    "amount_tao": order.amount_tao,
                    "status": "error",
                    "message": f"Unknown action: {order.action}",
                    "tx_hash": None,
                }

            return {
                "action": order.action,
                "netuid": order.netuid,
                "amount_tao": order.amount_tao,
                "status": "success" if result else "failed",
                "message": f"{'Staked' if order.action == 'stake' else 'Unstaked'} {order.amount_tao:.4f} TAO on subnet {order.netuid}",
                "tx_hash": str(result) if result else None,
            }

        except Exception as e:
            return {
                "action": order.action,
                "netuid": order.netuid,
                "amount_tao": order.amount_tao,
                "status": "error",
                "message": str(e),
                "tx_hash": None,
            }

    def format_results(self, results: list[dict]) -> str:
        """Format execution results as human-readable string."""
        lines = []
        for r in results:
            status_icon = {
                "dry_run": "🔍",
                "success": "✅",
                "failed": "❌",
                "error": "⚠️",
            }.get(r["status"], "?")
            lines.append(f"{status_icon} {r['message']}")
        return "\n".join(lines)
