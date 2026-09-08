require('dotenv').config();

const express = require('express');
const { JsonRpcProvider, isAddress, formatEther, getAddress } = require('ethers');

const { WalletManager } = require('./walletManager');

const app = express();
const port = process.env.PORT || 3000;
const rpcUrl = process.env.EVM_RPC_URL || 'https://ethereum-rpc.publicnode.com';
const maxAddresses = Number(process.env.MAX_ADDRESSES_PER_REQUEST) || 20;

const provider = new JsonRpcProvider(rpcUrl);

// Balance of a single address, as { address, wei, ether }.
async function readBalance(address) {
  const wei = await provider.getBalance(address);
  return { address, wei: wei.toString(), ether: formatEther(wei) };
}

// GET endpoint 1
app.get('/hello', (req, res) => {
  res.send('Hello, this is the first endpoint!');
});

// GET endpoint 2
app.get('/goodbye', (req, res) => {
  res.send('Goodbye, this is the second endpoint!');
});

// GET endpoint 4: total balance across several public addresses.
// Declared before /balance/:address so the bare path is not swallowed by it.
app.get('/balance', async (req, res) => {
  const { addresses } = req.query;

  if (typeof addresses !== 'string' || addresses.trim() === '') {
    return res.status(400).json({
      error: 'Query parameter "addresses" is required, comma-separated',
    });
  }

  const requested = addresses
    .split(',')
    .map((value) => value.trim())
    .filter((value) => value !== '');

  const invalid = requested.filter((value) => !isAddress(value));
  if (invalid.length > 0) {
    return res.status(400).json({ error: 'Invalid EVM address', invalid });
  }

  // Checksum first, so the same wallet written in different cases is counted once.
  const unique = [...new Set(requested.map((value) => getAddress(value)))];

  if (unique.length > maxAddresses) {
    return res.status(400).json({
      error: `Too many addresses, ${maxAddresses} at most`,
      received: unique.length,
    });
  }

  try {
    const balances = await Promise.all(unique.map(readBalance));
    const totalWei = balances.reduce((sum, item) => sum + BigInt(item.wei), 0n);

    res.json({
      count: balances.length,
      balances,
      total: { wei: totalWei.toString(), ether: formatEther(totalWei) },
    });
  } catch (err) {
    console.error(`Balance lookup failed for ${unique.join(', ')}:`, err.message);
    res.status(502).json({ error: 'Unable to reach the EVM node' });
  }
});

// GET endpoint 3: EVM wallet balance for a public address
app.get('/balance/:address', async (req, res) => {
  const { address } = req.params;

  if (!isAddress(address)) {
    return res.status(400).json({ error: 'Invalid EVM address' });
  }

  try {
    res.json(await readBalance(address));
  } catch (err) {
    console.error(`Balance lookup failed for ${address}:`, err.message);
    res.status(502).json({ error: 'Unable to reach the EVM node' });
  }
});

// GET endpoint 5: cached portfolio with a fiat estimate
const walletManager = new WalletManager(provider);
app.get('/portfolio', (req, res) => walletManager.handlePortfolio(req, res));

app.get('/test', (req, res) => console.log('je suis un test'))

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
