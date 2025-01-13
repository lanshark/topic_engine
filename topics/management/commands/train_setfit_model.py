import logging
import os

from datasets import Dataset
from django.conf import settings
from django.core.management.base import BaseCommand
from setfit import SetFitModel, Trainer, TrainingArguments

from core.models import ModelConfig

# Constants
TRAINING_DATA_DIR = os.path.join(settings.BASE_DIR, "topics", "training_data")
MODEL_SAVE_DIR = os.path.join(settings.BASE_DIR, "topics", "setfit_models")

# Recommended models
SUGGESTED_MODELS = {
    "small": "sentence-transformers/paraphrase-MiniLM-L3-v2",
    "medium": "sentence-transformers/all-MiniLM-L6-v2",
    "large": "sentence-transformers/all-mpnet-base-v2",
}


class Command(BaseCommand):
    help = "Train SetFit model with a given configuration"

    def add_arguments(self, parser):
        parser.add_argument("model_name", type=str, help="Name of the model configuration to use")

    def load_training_data(self, topic_name: str) -> Dataset:
        """Load training data from text files into HuggingFace Dataset"""
        topic_path = os.path.join(TRAINING_DATA_DIR, topic_name)
        if not os.path.exists(topic_path):
            raise ValueError(f"Training data path not found: {topic_path}")

        texts, labels = [], []

        # Load relevant examples
        relevant_path = os.path.join(topic_path, "relevant.txt")
        with open(relevant_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    texts.append(line)
                    labels.append(1)

        # Load irrelevant examples
        irrelevant_path = os.path.join(topic_path, "irrelevant.txt")
        with open(irrelevant_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    texts.append(line)
                    labels.append(0)

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(texts)} examples from {topic_path}"))

        return Dataset.from_dict({"text": texts, "label": labels})

    def handle(self, *args, **options):
        model_name = options["model_name"]
        try:
            model_config = ModelConfig.objects.get(name=model_name)
        except ModelConfig.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Model config '{model_name}' not found"))
            return

        # Load and split data
        dataset = self.load_training_data(model_config.topic.slug)
        dataset = dataset.train_test_split(test_size=0.2)

        # Configure model
        model_type = model_config.parameters.get("model_type", "medium")
        base_model = SUGGESTED_MODELS.get(model_type, SUGGESTED_MODELS["medium"])
        self.stdout.write(f"Using base model: {base_model}")

        # Initialize model
        model = SetFitModel.from_pretrained(base_model)

        # Get training parameters with defaults based on model type
        batch_size = model_config.parameters.get(
            "batch_size", {"small": 16, "medium": 8, "large": 4}.get(model_type, 8)
        )

        num_epochs = model_config.parameters.get(
            "num_epochs", {"small": 5, "medium": 3, "large": 8}.get(model_type, 3)
        )

        num_iterations = model_config.parameters.get(
            "num_iterations", {"small": 8, "medium": 20, "large": 12}.get(model_type, 20)
        )

        # Set up training arguments using setfit's TrainingArguments
        training_args = TrainingArguments(
            batch_size=batch_size, num_iterations=num_iterations, num_epochs=num_epochs
        )

        # Calculate and display training info
        total_steps = (len(dataset["train"]) // batch_size) * num_epochs
        self.stdout.write("\nTraining with:")
        self.stdout.write(f"- Batch size: {batch_size}")
        self.stdout.write(f"- Epochs: {num_epochs}")
        self.stdout.write(f"- Iterations: {num_iterations}")
        self.stdout.write(f"- Total steps: {total_steps}")

        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset["train"],
            eval_dataset=dataset["test"],
        )

        # Train model
        self.stdout.write("Starting training...")
        trainer.train()

        # Evaluate
        predictions = model.predict(dataset["test"]["text"])
        accuracy = sum(p == l for p, l in zip(predictions, dataset["test"]["label"])) / len(
            predictions
        )

        # Save model
        save_path = os.path.join(MODEL_SAVE_DIR, model_name)
        model.save_pretrained(save_path)

        # Update metrics
        model_config.update_training_metrics(num_examples=len(dataset["train"]), accuracy=accuracy)

        self.stdout.write(self.style.SUCCESS(f"Model trained and saved. Accuracy: {accuracy:.3f}"))
