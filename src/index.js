require('dotenv').config();

const express = require('express');
const { JsonRpcProvider, isAddress, formatEther } = require('ethers');

const app = express();
const port = process.env.PORT || 3000;
const rpcUrl = process.env.EVM_RPC_URL || 'https://ethereum-rpc.publicnode.com';

const provider = new JsonRpcProvider(rpcUrl);

// GET endpoint 1
app.get('/hello', (req, res) => {
  res.send('Hello, this is the first endpoint!');
});

// GET endpoint 2
app.get('/goodbye', (req, res) => {
  res.send('Goodbye, this is the second endpoint!');
});

// GET endpoint 3: EVM wallet balance for a public address
app.get('/balance/:address', async (req, res) => {
  const { address } = req.params;

  if (!isAddress(address)) {
    return res.status(400).json({ error: 'Invalid EVM address' });
  }

  try {
    const wei = await provider.getBalance(address);
    res.json({
      address,
      wei: wei.toString(),
      ether: formatEther(wei),
    });
  } catch (err) {
    console.error(`Balance lookup failed for ${address}:`, err.message);
    res.status(502).json({ error: 'Unable to reach the EVM node' });
  }
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
