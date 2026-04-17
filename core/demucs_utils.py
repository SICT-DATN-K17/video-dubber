import subprocess
from pathlib import Path

def separate_vocals(input_audio: str | Path, output_dir: str | Path = None, model: str = "htdemucs") -> Path:
    """
    Tách vocal (giọng nói) khỏi nhạc nền bằng Demucs.
    Trả về đường dẫn file vocal.wav đã tách.
    Yêu cầu: pip install demucs
    """
    input_audio = Path(input_audio)
    if output_dir is None:
        output_dir = input_audio.parent / f"demucs_{input_audio.stem}"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python", "-m", "demucs", "--two-stems", "vocals", "-n", model,
        "-o", str(output_dir), str(input_audio)
    ]
    subprocess.run(cmd, check=True)

    # Demucs sẽ tạo thư mục: output_dir/model_name/input_audio_stem/vocals.wav
    vocal_path = output_dir / model / input_audio.stem / "vocals.wav"
    if not vocal_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file vocal: {vocal_path}")
    return vocal_path
