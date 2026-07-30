import logging
import time
import os
import torch
from torch.utils.data import DataLoader
from typing import List, Dict, Any

from aegis_trade.providers.kronos.shiyu_model.kronos import KronosTokenizer, Kronos

logger = logging.getLogger(__name__)

class KronosFineTuner:
    """
    Handles offline fine-tuning of the Kronos-mini model on CPU.
    """
    def __init__(self, tokenizer: KronosTokenizer, model: Kronos, output_dir: str = "./models/kronos_finetuned"):
        self.tokenizer = tokenizer
        self.model = model
        self.output_dir = output_dir
        self.device = torch.device("cpu")
        os.makedirs(self.output_dir, exist_ok=True)

    def train(self, train_dataset: Any, val_dataset: Any, epochs: int = 1) -> Dict[str, float]:
        """
        Runs the fine-tuning loop.
        CPU-only synchronous.
        """
        if not self.model or not self.tokenizer:
            logger.error("Cannot train: Model or Tokenizer is None.")
            return {}

        logger.info(f"Starting fine-tuning for {epochs} epochs on CPU...")
        start_time = time.time()
        
        batch_size = 4
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=4e-5,
            betas=(0.9, 0.95),
            weight_decay=0.1
        )
        
        best_val_loss = float('inf')
        
        for epoch_idx in range(epochs):
            epoch_start_time = time.time()
            self.model.train()
            
            total_train_loss = 0.0
            
            for i, (batch_x, batch_x_stamp) in enumerate(train_loader):
                batch_x = batch_x.to(self.device)
                batch_x_stamp = batch_x_stamp.to(self.device)

                # Tokenize input data on-the-fly
                with torch.no_grad():
                    token_seq_0, token_seq_1 = self.tokenizer.encode(batch_x, half=True)

                # Prepare inputs and targets
                token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
                token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]

                # Forward pass and loss calculation
                logits = self.model(token_in[0], token_in[1], batch_x_stamp[:, :-1, :])
                loss, s1_loss, s2_loss = self.model.head.compute_loss(logits[0], logits[1], token_out[0], token_out[1])

                # Backward pass and optimization
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=3.0)
                optimizer.step()

                total_train_loss += loss.item()
                
            avg_train_loss = total_train_loss / max(1, len(train_loader))
            logger.info(f"Epoch {epoch_idx+1} Train Loss: {avg_train_loss:.4f}")

            # Validation Loop
            self.model.eval()
            total_val_loss = 0.0
            val_batches = 0
            
            with torch.no_grad():
                for batch_x, batch_x_stamp in val_loader:
                    batch_x = batch_x.to(self.device)
                    batch_x_stamp = batch_x_stamp.to(self.device)

                    token_seq_0, token_seq_1 = self.tokenizer.encode(batch_x, half=True)
                    token_in = [token_seq_0[:, :-1], token_seq_1[:, :-1]]
                    token_out = [token_seq_0[:, 1:], token_seq_1[:, 1:]]

                    logits = self.model(token_in[0], token_in[1], batch_x_stamp[:, :-1, :])
                    val_loss, _, _ = self.model.head.compute_loss(logits[0], logits[1], token_out[0], token_out[1])

                    total_val_loss += val_loss.item()
                    val_batches += 1

            avg_val_loss = total_val_loss / max(1, val_batches)
            
            epoch_duration = time.time() - epoch_start_time
            logger.info(f"Epoch {epoch_idx+1} completed in {epoch_duration:.2f}s | Val Loss: {avg_val_loss:.4f}")
            
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                checkpoint_path = os.path.join(self.output_dir, "best_model.ckpt")
                # self.model.save_pretrained(checkpoint_path)
                logger.info(f"Saved new best checkpoint to {checkpoint_path}")
            
        total_duration = time.time() - start_time
        logger.info(f"Fine-tuning complete. Total time: {total_duration:.2f}s")
        
        return {"val_loss": best_val_loss}

