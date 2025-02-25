import torch 
import torch.nn as nn
from torch.nn import functional as F


# hyperparams

# number of samples
batch_size = 32

# length of the samples
block_size = 8

max_iters = 3000
eval_interval = 300
learning_rate = 1e-2

# use gpu if available
device = 'cuda' if torch.cuda.is_available() else 'cpu'
eval_iters = 200
n_embd = 32

torch.manual_seed(1337)


# download shakespeare text
## !wget https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt

with open('input.txt', 'r', encoding="utf-8") as f:
    text = f.read()


## SETTING UP SIMPLE TOKENIZER
# have a list of individual characters
chars = sorted(list(set(text)))
vocab_size = len(chars)

stoi = { ch: i for i, ch in enumerate(chars) } # make a mapping of each character to its index
itos = { i: ch for i, ch in enumerate(chars) } # make a mapping of each index to its character
encode = lambda s: [stoi[c] for c in s] # give a list of each character in integer encoding form
decode = lambda l: ''.join([itos[i] for i in l]) # return a character from a list of index

# Train and test splits
data = torch.tensor(encode(text), dtype=torch.long)
n = int(0.9*len(data)) # first 90% will be train, rest val
train_data = data[:n]
val_data = data[n:]


# data loading
def get_batch(split):
    # generate a small batch of data of inputs x and targets y
    data = train_data if split == 'train' else val_data

    # generate batch_size(32) random numbers between 0 and len(data) - batch size(8), i.e. get 32 random indexes from 0 and len-batchsize(8)
    ix = torch.randint(len(data) - block_size, (batch_size,))

    # get a 2d array of [idx to idx + block_size]
    x = torch.stack([data[i:i+block_size] for i in ix])

    # get a 2d array of x+1, basically the result values
    y = torch.stack([data[i+1:i+block_size+1] for i in ix])
    x, y = x.to(device), y.to(device)
    return x,y


@torch.no_grad()
def estimate_loss():
    out = {}
    model.eval()
    for split in ['train', 'val']:
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            X, Y = get_batch(split)
            logits, loss = model(X, Y)
            losses[k] = loss.item()
        out[split] = losses.mean()
    model.train()
    return out


class BigramLanguageModel(nn.Module):

    def __init__(self):
        super().__init__()

        # setup embedding table for relationships
        self.token_embedding_table = nn.Embedding(vocab_size, n_embd)
        self.position_embedding_table = nn.Embedding(block_size, n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        
        # get all the embeddings
        tok_emb = self.token_embedding_table(idx) # (B,T,C)
        pos_emb = self.position_embedding_table(torch.arange(T, device=device)) # (T,C)
        x = tok_emb + pos_emb # (B,T,C)
        logits = self.lm_head(x) #(B,T,vocab_size)
        

        if targets is None:
            loss = None
        else:
            # get the Batch size, Time/block size and Channel/vocab_size
            B, T, C = logits.shape
            logits = logits.view(B*T, C)
            targets = targets.view(B*T)
            loss = F.cross_entropy(logits, targets)
        return logits, loss
    
    def generate(self, idx, max_new_tokens):
        for _ in range(max_new_tokens):
            logits, loss = self(idx) # get prediction
            logits = logits[:, -1, :] # becomes (B, C)
            # apply softmax to get probabilities
            probs = F.softmax(logits, dim=-1) # (B, C)
            # sample from the distribution
            idx_next = torch.multinomial(probs, num_samples=1) # (B, 1)
            idx = torch.cat((idx, idx_next), dim=1) # (B, T+1)
        return idx

model = BigramLanguageModel()
m = model.to(device)

optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

for iter in range(max_iters):
    if iter % eval_interval == 0:
        losses = estimate_loss()
        print(f"steps {iter}: train loss {losses['train']:.4f}, val loss {losses['val']:.4f}")

    xb, yb = get_batch('train')

    logits, loss = model(xb, yb)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()

context = torch.zeros((1, 1), dtype=torch.long, device=device)
print(decode(m.generate(context, max_new_tokens=500)[0].tolist()))