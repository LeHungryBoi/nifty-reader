use hf_hub::{
    api::sync::Api,
    Repo, RepoType,
};
use std::{
    error::Error,
    fs,
    io,
    path::{Path, PathBuf},
};

fn main() -> Result<(), Box<dyn Error>> {
    let root = repo_root()?;
    let models_dir = root.join("models");

    let pocket_repo = Repo::with_revision(
        "kyutai/pocket-tts".to_string(),
        RepoType::Model,
        "main".to_string(),
    );
    let wav2vec_repo = Repo::with_revision(
        "facebook/wav2vec2-base-960h".to_string(),
        RepoType::Model,
        "main".to_string(),
    );

    let pocket_files = [
        "languages/english_2026-04/config.json",
        "languages/english_2026-04/model.safetensors",
        "languages/english_2026-04/vocab.json",
    ];

    let wav2vec_files = [
        "config.json",
        "preprocessor_config.json",
        "tokenizer.json",
        "vocab.json",
        "pytorch_model.bin",
    ];

    let pocket_out = models_dir.join("pocket-tts/english_2026-04");
    let wav2vec_out = models_dir.join("wav2vec2/facebook-wav2vec2-base-960h");

    fetch_model_files(&pocket_repo, &pocket_files, &pocket_out)?;
    fetch_model_files(&wav2vec_repo, &wav2vec_files, &wav2vec_out)?;

    write_lockfile(&models_dir)?;

    println!("TTS models ready under {}", models_dir.display());
    Ok(())
}

fn fetch_model_files(
    repo: &Repo,
    files: &[&str],
    output_dir: &Path,
) -> Result<(), Box<dyn Error>> {
    fs::create_dir_all(output_dir)?;

    let api = Api::new()?;
    let model = api.repo(repo.clone());

    for file in files {
        let source = model.get(file)?;
        let destination = output_dir.join(
            Path::new(file)
                .file_name()
                .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "Invalid model filename"))?,
        );

        if destination.exists() {
            println!("skip: {}", destination.display());
            continue;
        }

        fs::copy(&source, &destination)?;
        println!("downloaded: {}", destination.display());
    }

    Ok(())
}

fn write_lockfile(models_dir: &Path) -> Result<(), Box<dyn Error>> {
    let lock = r#"[pocket_tts_english_2026_04]
source = "https://huggingface.co/kyutai/pocket-tts/tree/main/languages/english_2026-04"
path = "models/pocket-tts/english_2026-04"

[wav2vec2_base_960h]
source = "https://huggingface.co/facebook/wav2vec2-base-960h"
path = "models/wav2vec2/facebook-wav2vec2-base-960h"
"#;

    fs::create_dir_all(models_dir)?;
    fs::write(models_dir.join("models.lock"), lock)?;
    Ok(())
}

fn repo_root() -> Result<PathBuf, Box<dyn Error>> {
    let cwd = std::env::current_dir()?;

    if cwd.join("Cargo.toml").exists() {
        return Ok(cwd);
    }

    if let Some(parent) = cwd.parent()
        && parent.join("Cargo.toml").exists()
    {
        return Ok(parent.to_path_buf());
    }

    Err("Could not locate repository root (Cargo.toml missing)".into())
}
