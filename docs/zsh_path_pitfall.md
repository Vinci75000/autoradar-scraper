# zsh `path` tied variable pitfall

## TL;DR

In zsh, **never use `path` (lowercase) as a variable name in shell blocks**.
It's a tied alias for `$PATH` and assigning to it silently breaks the shell.

## The bug

zsh maintains tied (linked) variables for several PATH-like environment
variables. The classic pair:

| Tied array (lowercase)   | Linked colon-separated string |
|--------------------------|-------------------------------|
| `path`                   | `PATH`                        |
| `cdpath`                 | `CDPATH`                      |
| `fpath`                  | `FPATH`                       |
| `manpath`                | `MANPATH`                     |
| `module_path`            | `MODULE_PATH`                 |

Any assignment to the lowercase form mutates the uppercase form and
vice-versa.

## Reproducing the bug

```zsh
% echo $PATH
/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin

% for path in "/foo" "/bar" "/baz"; do
    echo "iter: $path"
  done
iter: /foo
iter: /bar
iter: /baz

% echo $PATH
/baz                    # ← broken: $PATH now contains only "/baz"

% which python3
python3 not found       # ← all binaries inaccessible
```

The loop variable `path` ends with the last iterated value, and because
of the tied alias, `$PATH` is rewritten to that single string.

## Recovery

```zsh
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH
```

(or close the terminal and re-open — `.zshrc` will rebuild PATH cleanly)

## Prevention

**Don't use these names as loop or scratch variables in shell blocks**:
- `path`, `cdpath`, `fpath`, `manpath`, `module_path`

**Safe alternatives**:
- `pth`, `subpath`, `p`
- `url`, `loc`, `endpoint`
- `dir`, `folder`
- `f` (file), `n` (item), `i` (index)

## Examples (do / don't)

```zsh
# ✗ DANGEROUS
for path in "/sitemap.xml" "/sitemap-cars.xml" "/listings.xml"; do
  curl -I "https://example.com$path"
done
# After: $PATH is broken.

# ✓ SAFE
for pth in "/sitemap.xml" "/sitemap-cars.xml" "/listings.xml"; do
  curl -I "https://example.com$pth"
done
```

## Optional: defensive shell setup

Add to `~/.zshrc` to warn (not block) when scripts assign to global vars
inside functions:

```zsh
setopt WARN_CREATE_GLOBAL
```

This won't catch ad-hoc shell loops at the prompt (where the bug usually
strikes), but helps in scripts.

## Reference

- zsh manual, section "Parameters": tied variables introduced via `typeset -T`
- `path` is created at zsh startup with `typeset -aT PATH path` internally

## Where this bit us

May 2026 sessions: AI assistant blocks used `for path in ...` in shell
diagnostics, breaking `$PATH` in the user's interactive session and
forcing manual recovery. Now documented to prevent recurrence.
