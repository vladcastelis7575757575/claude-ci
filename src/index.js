const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

// GET endpoint 1
app.get('/hello', (req, res) => {
  res.send('Hello, this is the first endpoint!');
});

// GET endpoint 2
app.get('/goodbye', (req, res) => {
  res.send('Goodbye, this is the second endpoint!');
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
