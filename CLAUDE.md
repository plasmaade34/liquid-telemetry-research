# Working style

State findings and answers directly. Don't wrap them in disclaimers,
caveats, or "here's what could go wrong" preamble unless something is
actually wrong or unverified. Do the checking; don't narrate the
checking. Answer first, keep it short, skip the hedging.

# Public repository rules

This repo is public. Everything in it, including commit messages, branch
names, notebook outputs and file headers, is published the moment it is
pushed to any branch.

- Before adding or pushing anything new, run the `hh-ip-safety-check`
  skill on it. If it reports "Needs changes", do not push; ask Ade.
- Never name internal projects, filing or patent status, partners, or
  specific sensor hardware in code, comments, commit messages, branch
  names or docs.
- Only generic, textbook-level material belongs here. Methods, tuning,
  results and simulations tied to the product go to a private repo.
- Never commit API keys or tokens. Read them from Colab Secrets or
  environment variables.
- Commit messages describe the change neutrally ("Remove unused
  notebook"), never why material is sensitive.
- When unsure, keep it local and ask.
