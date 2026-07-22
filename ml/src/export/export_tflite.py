"""
SnapMenu ML - Export to TFLite
================================
Exports trained PyTorch model to TFLite for on-device inference.

Pipeline: PyTorch → ONNX → TFLite (with INT8 quantization)

The exported model will be used in the Flutter app via tflite_flutter plugin.

Usage:
    python -m src.export.export_tflite \
        --model models/snapmenu_classifier_final.pth \
        --output models/snapmenu_v1.tflite \
        --quantize int8 \
        --calibration-dir ./data/splits/val
"""

import os
import argparse
from pathlib import Path

import yaml
import torch
import torch.nn as nn
import numpy as np
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader


def load_trained_model(model_path: str, device: torch.device) -> tuple:
    """Load the trained PyTorch model."""
    checkpoint = torch.load(model_path, map_location=device)

    class_names = checkpoint.get('class_names', [])
    num_classes = checkpoint.get('num_classes', len(class_names))
    config = checkpoint.get('config', {})

    model_arch = config.get('model', {}).get('architecture', 'efficientnet_v2_s')
    dropout = config.get('model', {}).get('dropout', 0.3)

    if model_arch == "efficientnet_v2_s":
        model = models.efficientnet_v2_s(weights=None)
    elif model_arch == "efficientnet_v2_m":
        model = models.efficientnet_v2_m(weights=None)
    else:
        model = models.efficientnet_v2_s(weights=None)

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout, inplace=True),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=dropout / 2),
        nn.Linear(512, num_classes),
    )

    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    return model, class_names, num_classes


def export_to_onnx(model: nn.Module, output_path: Path, img_size: int = 224):
    """Export PyTorch model to ONNX format."""
    print("\n📦 Step 1: Exporting to ONNX...")

    dummy_input = torch.randn(1, 3, img_size, img_size)

    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=None,  # Fixed size for mobile
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ ONNX saved: {output_path} ({size_mb:.1f} MB)")
    return output_path


def export_to_tflite(
    onnx_path: Path,
    output_path: Path,
    quantize: str = "none",
    calibration_dir: str = None,
    num_calibration_samples: int = 300,
    img_size: int = 224,
):
    """Convert ONNX model to TFLite with optional quantization."""
    print(f"\n📦 Step 2: Converting to TFLite (quantization: {quantize})...")

    try:
        import onnx
        from onnx_tf.backend import prepare
        import tensorflow as tf
    except ImportError:
        print("   ❌ Required packages not installed. Run:")
        print("      pip install onnx onnx-tf tensorflow")
        print("\n   Alternative: Use the Kaggle notebook which has these pre-installed.")
        _export_tflite_via_ai_edge(onnx_path, output_path, quantize, calibration_dir, num_calibration_samples, img_size)
        return

    # Load ONNX model
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    # Convert ONNX → TensorFlow SavedModel
    print("   Converting ONNX → TensorFlow...")
    tf_rep = prepare(onnx_model)
    saved_model_dir = output_path.parent / "tf_saved_model"
    tf_rep.export_graph(str(saved_model_dir))

    # Convert TF SavedModel → TFLite
    print("   Converting TensorFlow → TFLite...")
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))

    if quantize == "fp16":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
        print("   Using FP16 quantization")

    elif quantize == "int8":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.float32

        # Representative dataset for calibration
        if calibration_dir:
            print(f"   Loading calibration data from: {calibration_dir}")

            def representative_dataset():
                transform = transforms.Compose([
                    transforms.Resize(256),
                    transforms.CenterCrop(img_size),
                    transforms.ToTensor(),
                ])
                dataset = datasets.ImageFolder(calibration_dir, transform=transform)
                indices = np.random.choice(len(dataset), min(num_calibration_samples, len(dataset)), replace=False)
                for idx in indices:
                    img, _ = dataset[idx]
                    img = img.unsqueeze(0).numpy()
                    yield [img.astype(np.float32)]

            converter.representative_dataset = representative_dataset
            print(f"   Using {num_calibration_samples} calibration samples for INT8")
        else:
            print("   ⚠️  No calibration data — using default quantization (less accurate)")

    elif quantize == "dynamic":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        print("   Using dynamic range quantization")

    tflite_model = converter.convert()

    # Save TFLite model
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ TFLite saved: {output_path} ({size_mb:.1f} MB)")

    # Cleanup temp SavedModel
    import shutil
    if saved_model_dir.exists():
        shutil.rmtree(saved_model_dir)


def _export_tflite_via_ai_edge(
    onnx_path: Path,
    output_path: Path,
    quantize: str,
    calibration_dir: str,
    num_calibration_samples: int,
    img_size: int,
):
    """Alternative export path using ai-edge-torch (PyTorch → TFLite directly)."""
    print("\n   Trying alternative: ai-edge-torch (direct PyTorch → TFLite)...")
    try:
        import ai_edge_torch
        print("   ⚠️  ai-edge-torch available but requires model object.")
        print("   Please use the Kaggle notebook for full export pipeline.")
    except ImportError:
        print("\n   📋 MANUAL EXPORT INSTRUCTIONS:")
        print("   ─────────────────────────────────")
        print("   Since TensorFlow is not installed here, use the Kaggle notebook")
        print("   (notebooks/snapmenu_training.ipynb) which handles the full pipeline:")
        print("   PyTorch → ONNX → TFLite with INT8 quantization.")
        print("")
        print("   Or install locally:")
        print("     pip install onnx onnx-tf tensorflow==2.15")
        print("     python -m src.export.export_tflite --model <path> --output <path>")


def validate_tflite(tflite_path: Path, img_size: int = 224):
    """Validate the exported TFLite model with a dummy input."""
    print("\n🧪 Step 3: Validating TFLite model...")

    try:
        import tensorflow as tf
    except ImportError:
        print("   ⚠️  TensorFlow not available — skipping validation")
        return

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print(f"   Input:  shape={input_details[0]['shape']} dtype={input_details[0]['dtype']}")
    print(f"   Output: shape={output_details[0]['shape']} dtype={output_details[0]['dtype']}")

    # Run dummy inference
    input_shape = input_details[0]['shape']
    input_dtype = input_details[0]['dtype']

    if input_dtype == np.uint8:
        dummy_input = np.random.randint(0, 255, size=input_shape).astype(np.uint8)
    else:
        dummy_input = np.random.randn(*input_shape).astype(np.float32)

    interpreter.set_tensor(input_details[0]['index'], dummy_input)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])

    print(f"   Output shape: {output.shape}")
    print(f"   Output range: [{output.min():.4f}, {output.max():.4f}]")
    print(f"   ✅ TFLite model validated successfully!")


def create_metadata_file(output_path: Path, class_names: list, img_size: int):
    """Create metadata JSON for the Flutter app to use with the model."""
    import json

    metadata = {
        "model_name": "snapmenu_ingredient_classifier",
        "version": "1.0.0",
        "input_size": img_size,
        "input_channels": 3,
        "normalize": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        "num_classes": len(class_names),
        "class_names": class_names,
        "confidence_threshold": 0.7,
        "top_k": 3,
    }

    metadata_path = output_path.parent / "model_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"   📋 Metadata saved: {metadata_path}")
    return metadata_path


def main():
    parser = argparse.ArgumentParser(description="Export SnapMenu model to TFLite")
    parser.add_argument('--model', type=str, required=True, help='Path to trained .pth model')
    parser.add_argument('--output', type=str, default='models/snapmenu_v1.tflite')
    parser.add_argument('--quantize', type=str, default='int8',
                        choices=['none', 'dynamic', 'fp16', 'int8'])
    parser.add_argument('--calibration-dir', type=str, default=None,
                        help='Path to calibration images (for INT8)')
    parser.add_argument('--img-size', type=int, default=224)
    parser.add_argument('--skip-validation', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print("🍽️  SnapMenu ML - Export to TFLite")
    print("=" * 60)

    device = torch.device('cpu')  # Export always on CPU

    # Load model
    print(f"\n  Loading model: {args.model}")
    model, class_names, num_classes = load_trained_model(args.model, device)
    print(f"  Classes: {num_classes}")
    print(f"  Class names: {class_names[:5]}... (and {num_classes - 5} more)")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Export to ONNX
    onnx_path = output_path.with_suffix('.onnx')
    export_to_onnx(model, onnx_path, args.img_size)

    # Step 2: Convert to TFLite
    export_to_tflite(
        onnx_path, output_path,
        quantize=args.quantize,
        calibration_dir=args.calibration_dir,
        num_calibration_samples=300,
        img_size=args.img_size,
    )

    # Step 3: Validate
    if not args.skip_validation and output_path.exists():
        validate_tflite(output_path, args.img_size)

    # Step 4: Create metadata for Flutter
    create_metadata_file(output_path, class_names, args.img_size)

    # Summary
    print(f"\n{'='*60}")
    print(f"  ✅ EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"  ONNX:     {onnx_path}")
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  TFLite:   {output_path} ({size_mb:.1f} MB)")
    print(f"  Metadata: {output_path.parent / 'model_metadata.json'}")
    print(f"\n  Next step: Copy .tflite + metadata.json to Flutter assets/models/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
