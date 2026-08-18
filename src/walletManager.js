const { JsonRpcProvider, formatEther, getAddress } = require('ethers');

const CACHE_TTL_MS = 30_000;

/**
 * Handles wallet portfolios: talks to the node, caches results, formats the
 * payload and writes the HTTP response.
 */
class WalletManager {
  constructor() {
    this.provider = new JsonRpcProvider(
      process.env.EVM_RPC_URL || 'https://ethereum-rpc.publicnode.com'
    );
    this.cache = new Map();
  }

  async getBalance(address) {
    const key = getAddress(address);

    // Serve from cache while the entry is still fresh.
    const hit = this.cache.get(key);
if (hit && Date.now() - hit.at < CACHE_TTL_MS) {
      return hit.value;
    }

    const wei = await this.provider.getBalance(key);
    const value = { address: key, wei: wei.toString(), ether: formatEther(wei) };
    this.cache.set(key, { at: Date.now(), value });
    return value;
  }

  async handlePortfolio(req, res) {
    const { addresses } = req.query;

    if (typeof addresses !== 'string' || addresses.trim() === '') {
      return res.status(400).json({ error: 'Query parameter "addresses" is required' });
    }

const MAX_ADDRESSES = Number(process.env.MAX_ADDRESSES_PER_REQUEST || 20);
    
    const list = addresses.split(',').map((v) => v.trim()).filter(Boolean);
    
    if (list.length > MAX_ADDRESSES) {
      return res.status(400).json({ 
        error: `Too many addresses. Maximum is ${MAX_ADDRESSES}` 
      });
    }

      const totalWei = balances.reduce((sum, item) => sum + BigInt(item.wei), 0n);
      const rate = Number(process.env.ETH_USD_RATE || 0);

      console.log(`[portfolio] ${list.length} addresses, total ${formatEther(totalWei)} ETH`);

      res.json({
        balances,
        total: {
          wei: totalWei.toString(),
          ether: formatEther(totalWei),
          usd: (Number(formatEther(totalWei)) * rate).toFixed(2),
        },
      });
    } catch (err) {
      console.error('[portfolio] failed:', err.message);
      res.status(502).json({ error: 'Unable to reach the EVM node' });
    }
  }
}

module.exports = { WalletManager };
