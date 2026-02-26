import json
import os
import time
from typing import Any, Dict, List, Tuple

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


QUALITY_PROFILES = {
    "fast": {
        "temperature": 0.35,
        "max_attempts": 2,
        "max_tokens": 5200,
        "strictness": "low",
    },
    "balanced": {
        "temperature": 0.55,
        "max_attempts": 3,
        "max_tokens": 9000,
        "strictness": "medium",
    },
    "premium": {
        "temperature": 0.7,
        "max_attempts": 4,
        "max_tokens": 14000,
        "strictness": "high",
    },
}

DEFAULT_TEMPLATE_SEED = {
    "html": """<main class=\"layout\">\n  <header class=\"hero\">\n    <p class=\"eyebrow\">Brand Value</p>\n    <h1>Compelling headline focused on customer outcome</h1>\n    <p>Short supporting copy that explains the product in plain language.</p>\n    <div class=\"hero-actions\">\n      <button class=\"btn primary\">Get Started</button>\n      <button class=\"btn secondary\">View Demo</button>\n    </div>\n  </header>\n\n  <section class=\"features\" aria-label=\"Core features\">\n    <article class=\"card\"><h2>Feature One</h2><p>Practical business value statement.</p></article>\n    <article class=\"card\"><h2>Feature Two</h2><p>Practical business value statement.</p></article>\n    <article class=\"card\"><h2>Feature Three</h2><p>Practical business value statement.</p></article>\n  </section>\n\n  <section class=\"cta\">\n    <h2>Ready to move faster?</h2>\n    <p>Single clear call to action.</p>\n    <button class=\"btn primary\">Start Free</button>\n  </section>\n</main>""",
    "css": """* { box-sizing: border-box; }\nbody { margin: 0; font-family: 'Manrope', 'Segoe UI', sans-serif; }\n.layout { max-width: 1120px; margin: 0 auto; padding: 2rem 1rem 4rem; }\n.hero { border-radius: 20px; padding: 2rem; }\n.hero-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }\n.features { margin-top: 1rem; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }\n.card { border-radius: 16px; padding: 1rem; }\n.btn { border-radius: 10px; padding: 0.7rem 1rem; cursor: pointer; border: 0; }\n@media (max-width: 900px) { .features { grid-template-columns: 1fr; } }""",
    "js": """document.addEventListener('DOMContentLoaded', () => {\n  // Attach interactions only if required by generated components.\n});""",
}


class WebsiteGenerator:
    def __init__(self):
        self.provider = os.getenv("GENERATOR_PROVIDER", "groq").strip().lower()
        self.allow_fallback = os.getenv("GENERATOR_ALLOW_FALLBACK", "false").strip().lower() == "true"
        self.api_key = self._resolve_api_key()
        self.base_url = self._resolve_base_url()
        self.model = self._resolve_model()

    def health_check(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "provider": self.provider,
            "sdk_available": OpenAI is not None,
            "key_present": bool(self.api_key),
            "base_url": self.base_url,
            "model": self.model,
            "model_available": False,
            "ok": False,
            "message": "",
        }

        if self.provider not in {"groq", "openai", "fallback"}:
            info["message"] = "Invalid provider. Use groq/openai/fallback."
            return info

        if self.provider == "fallback":
            info["ok"] = True
            info["model_available"] = True
            info["message"] = "Fallback mode is active."
            return info

        if OpenAI is None:
            info["message"] = "Python package 'openai' is not installed."
            return info

        if not self.api_key:
            info["message"] = self._missing_key_message()
            return info

        try:
            client = self._client()
            models = client.models.list()
            model_ids = [m.id for m in getattr(models, "data", [])]
            info["model_available"] = self.model in model_ids if model_ids else True
            info["ok"] = bool(info["model_available"])
            info["message"] = (
                "Provider is healthy." if info["ok"] else f"Configured model '{self.model}' is not listed by provider."
            )
            return info
        except Exception as exc:
            info["message"] = f"Provider connectivity failed: {str(exc)}"
            return info

    def generate(
        self,
        prompt: str,
        style: str,
        pages: int,
        strict_mode: bool = True,
        quality_preset: str = "balanced",
        rewrite_mode: bool = True,
    ) -> Dict[str, Any]:
        quality = QUALITY_PROFILES.get(quality_preset, QUALITY_PROFILES["balanced"])
        logs: Dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "strict_mode": strict_mode,
            "quality_preset": quality_preset if quality_preset in QUALITY_PROFILES else "balanced",
            "rewrite_mode": rewrite_mode,
            "attempts": [],
            "errors": [],
            "warnings": [],
            "enhanced_spec": {},
            "latency_ms": 0,
        }

        start = time.perf_counter()

        if self.provider in {"groq", "openai"} and self.api_key and OpenAI is not None:
            try:
                result = self._generate_llm(
                    prompt=prompt,
                    style=style,
                    pages=pages,
                    strict_mode=strict_mode,
                    quality=quality,
                    rewrite_mode=rewrite_mode,
                    logs=logs,
                )
                logs["latency_ms"] = int((time.perf_counter() - start) * 1000)
                result["logs"] = logs
                return result
            except ValueError as exc:
                logs["errors"].append(str(exc))
                if strict_mode:
                    raise
            except Exception as exc:
                logs["errors"].append(f"LLM call failed: {str(exc)}")
                if strict_mode:
                    raise ValueError(f"Live model generation failed: {str(exc)}")

        if strict_mode:
            raise ValueError(self._build_live_mode_error())

        if self.allow_fallback or self.provider == "fallback" or not strict_mode:
            fallback_reason = logs["errors"][-1] if logs["errors"] else "Provider key missing or SDK unavailable."
            result = self._generate_fallback(prompt=prompt, style=style, pages=pages, reason=fallback_reason)
            logs["latency_ms"] = int((time.perf_counter() - start) * 1000)
            result["logs"] = logs
            return result

        raise ValueError(self._build_live_mode_error())

    def _resolve_api_key(self) -> str:
        if self.provider == "groq":
            return os.getenv("GROQ_API_KEY", "").strip()
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY", "").strip()
        return ""

    def _resolve_base_url(self) -> str:
        if self.provider == "groq":
            return os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
        if self.provider == "openai":
            return os.getenv("OPENAI_BASE_URL", "").strip()
        return ""

    def _resolve_model(self) -> str:
        if self.provider == "groq":
            return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
        return ""

    def _missing_key_message(self) -> str:
        if self.provider == "groq":
            return "Missing GROQ_API_KEY."
        if self.provider == "openai":
            return "Missing OPENAI_API_KEY."
        return "Missing provider API key."

    def _build_live_mode_error(self) -> str:
        if self.provider not in {"groq", "openai", "fallback"}:
            return "Invalid GENERATOR_PROVIDER. Use 'groq', 'openai', or 'fallback'."
        if OpenAI is None:
            return "Python package 'openai' is not installed. Run: pip install -r requirements.txt"
        if not self.api_key:
            return f"{self._missing_key_message()} Set it in .env and restart Flask."
        return "Live model configuration is invalid."

    def _resolve_generation_budget(self, quality: Dict[str, Any], pages: int) -> Dict[str, int]:
        # Scale effort for larger page counts so model has enough room to complete output.
        scaled_attempts = min(quality["max_attempts"] + (1 if pages >= 4 else 0), 5)
        scaled_tokens = min(quality["max_tokens"] + (pages - 1) * 1400, 16000)
        return {"max_attempts": scaled_attempts, "max_tokens": scaled_tokens}

    def _client(self) -> OpenAI:
        client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        return OpenAI(**client_kwargs)

    def _enhance_prompt_spec(self, prompt: str, style: str, pages: int) -> Dict[str, Any]:
        prompt_l = prompt.lower()
        section_rules = {
            "hero": ["landing", "homepage", "hero", "saas", "startup"],
            "features": ["feature", "product", "platform", "tool"],
            "pricing": ["pricing", "plan", "subscription"],
            "testimonials": ["testimonial", "review", "social proof"],
            "faq": ["faq", "questions", "support"],
            "contact": ["contact", "lead", "demo", "book"],
            "portfolio": ["portfolio", "project", "case study", "work"],
            "team": ["team", "about", "company"],
        }

        inferred_sections: List[str] = []
        for section, keywords in section_rules.items():
            if any(word in prompt_l for word in keywords):
                inferred_sections.append(section)

        if not inferred_sections:
            inferred_sections = ["hero", "features", "cta", "contact"]

        if "enterprise" in prompt_l or "b2b" in prompt_l:
            tone = "professional and confident"
            audience = "B2B decision makers"
        elif "portfolio" in prompt_l or "creator" in prompt_l:
            tone = "personal and creative"
            audience = "clients and collaborators"
        elif "ecommerce" in prompt_l or "shop" in prompt_l or "store" in prompt_l:
            tone = "commercial and trust-building"
            audience = "online buyers"
        else:
            tone = "clear and conversion-focused"
            audience = "general product users"

        cta = "Get Started"
        if "book" in prompt_l or "demo" in prompt_l:
            cta = "Book a Demo"
        elif "portfolio" in prompt_l:
            cta = "View Projects"
        elif "shop" in prompt_l or "store" in prompt_l:
            cta = "Shop Now"

        return {
            "goal": prompt,
            "style": style,
            "pages": pages,
            "tone": tone,
            "target_audience": audience,
            "primary_cta": cta,
            "sections": inferred_sections,
        }

    def _build_generation_prompts(
        self,
        enhanced_spec: Dict[str, Any],
        rewrite_mode: bool,
        strictness: str,
        validation_feedback: str,
    ) -> Tuple[str, str]:
        system_prompt = (
            "You are a senior frontend engineer and UX writer. "
            "Generate production-quality multi-section webpages from intent. "
            "Never copy the raw user prompt as visible page text. "
            "Output strict JSON only with keys: title, summary, pages. "
            "Each page item must include: name, html, css, js. "
            "HTML must be semantic and accessible. CSS must be mobile-first responsive. "
            "JS should be minimal and unobtrusive. "
            "No markdown fences, no extra keys, no explanation."
        )

        rewrite_instruction = ""
        if rewrite_mode:
            rewrite_instruction = (
                "Use this seed as structural baseline and rewrite it heavily to match the spec, "
                "including layout decisions, copy, and component hierarchy:\n"
                f"SEED_HTML:\n{DEFAULT_TEMPLATE_SEED['html']}\n"
                f"SEED_CSS:\n{DEFAULT_TEMPLATE_SEED['css']}\n"
                f"SEED_JS:\n{DEFAULT_TEMPLATE_SEED['js']}\n"
            )

        user_prompt = (
            f"Build {enhanced_spec['pages']} page(s).\n"
            f"Goal: {enhanced_spec['goal']}\n"
            f"Style direction: {enhanced_spec['style']}\n"
            f"Tone: {enhanced_spec['tone']}\n"
            f"Target audience: {enhanced_spec['target_audience']}\n"
            f"Primary CTA: {enhanced_spec['primary_cta']}\n"
            f"Required sections: {', '.join(enhanced_spec['sections'])}\n"
            f"Strictness profile: {strictness}\n"
            "Return pragmatic, realistic marketing copy, not placeholder text.\n"
        )

        if rewrite_instruction:
            user_prompt += rewrite_instruction

        if validation_feedback:
            user_prompt += (
                "Fix these quality issues from prior attempt:\n"
                f"{validation_feedback}\n"
            )

        return system_prompt, user_prompt

    def _generate_llm(
        self,
        prompt: str,
        style: str,
        pages: int,
        strict_mode: bool,
        quality: Dict[str, Any],
        rewrite_mode: bool,
        logs: Dict[str, Any],
    ) -> Dict[str, Any]:
        enhanced_spec = self._enhance_prompt_spec(prompt=prompt, style=style, pages=pages)
        logs["enhanced_spec"] = enhanced_spec

        client = self._client()
        validation_feedback = ""
        budget = self._resolve_generation_budget(quality=quality, pages=pages)
        best_candidate: Dict[str, Any] = {}
        best_score = 10**9

        for attempt in range(1, budget["max_attempts"] + 1):
            attempt_log: Dict[str, Any] = {
                "attempt": attempt,
                "temperature": quality["temperature"],
                "critical_errors": [],
                "soft_errors": [],
                "parse_error": "",
            }

            system_prompt, user_prompt = self._build_generation_prompts(
                enhanced_spec=enhanced_spec,
                rewrite_mode=rewrite_mode,
                strictness=quality["strictness"],
                validation_feedback=validation_feedback,
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=quality["temperature"],
                response_format={"type": "json_object"},
                max_tokens=budget["max_tokens"],
            )

            raw_text = (response.choices[0].message.content or "").strip()
            if not raw_text:
                attempt_log["parse_error"] = "Empty response"
                logs["attempts"].append(attempt_log)
                validation_feedback = "Model returned empty output."
                continue

            try:
                data = self._parse_json_payload(raw_text)
            except Exception as exc:
                attempt_log["parse_error"] = str(exc)
                logs["attempts"].append(attempt_log)
                validation_feedback = "Return strict valid JSON with title, summary, pages[]."
                continue

            pages_data = data.get("pages") or []
            normalized_pages = [self._normalize_page(page, idx) for idx, page in enumerate(pages_data)]
            attempt_log["page_count"] = len(normalized_pages)

            if not normalized_pages:
                attempt_log["critical_errors"] = ["No pages returned."]
                logs["attempts"].append(attempt_log)
                validation_feedback = "You must return at least one page object."
                continue

            validation = self._validate_output(
                pages=normalized_pages,
                original_prompt=prompt,
                strictness=quality["strictness"],
            )
            attempt_log["critical_errors"] = validation["critical"]
            attempt_log["soft_errors"] = validation["soft"]
            logs["attempts"].append(attempt_log)

            score = len(validation["critical"]) * 100 + len(validation["soft"])
            if score < best_score:
                best_score = score
                best_candidate = {
                    "title": data.get("title", "Generated Website"),
                    "summary": data.get("summary", "Generated from prompt."),
                    "pages": normalized_pages,
                    "source": self.provider,
                    "validation": validation,
                }

            if validation["critical"] or validation["soft"]:
                all_issues = validation["critical"] + validation["soft"]
                validation_feedback = "\n".join(f"- {item}" for item in all_issues)
                continue

            return {
                "title": data.get("title", "Generated Website"),
                "summary": data.get("summary", "Generated from prompt."),
                "pages": normalized_pages,
                "source": self.provider,
            }

        if best_candidate:
            critical = best_candidate["validation"]["critical"]
            soft = best_candidate["validation"]["soft"]

            if critical:
                if strict_mode:
                    raise ValueError("Model output was incomplete after retries. Try fewer pages or premium preset.")
                fallback = self._generate_fallback(
                    prompt=prompt,
                    style=style,
                    pages=pages,
                    reason="Critical validation errors remained after retries.",
                )
                return fallback

            if soft:
                logs["warnings"].append(
                    "Returned best validated output with minor quality warnings: "
                    + "; ".join(soft[:4])
                )
                best_candidate.pop("validation", None)
                return best_candidate

        if strict_mode:
            raise ValueError("Model output failed quality validation after retries. Try premium preset or fewer pages.")

        return self._generate_fallback(
            prompt=prompt,
            style=style,
            pages=pages,
            reason="Model output failed validation; returned fallback due to non-strict mode.",
        )

    def _validate_output(self, pages: List[Dict[str, str]], original_prompt: str, strictness: str) -> Dict[str, List[str]]:
        critical: List[str] = []
        soft: List[str] = []
        prompt_lower = original_prompt.lower()

        generic_markers = [
            "lorem ipsum",
            "your company",
            "insert text",
            "sample text",
            "placeholder",
        ]

        for idx, page in enumerate(pages):
            html = (page.get("html") or "").lower()
            css = (page.get("css") or "").lower()

            if len(html) < 220:
                critical.append(f"Page {idx + 1} HTML is too short.")
            elif len(html) < 340 and strictness in {"medium", "high"}:
                soft.append(f"Page {idx + 1} HTML could be richer.")

            if "<main" not in html and "<section" not in html:
                critical.append(f"Page {idx + 1} is missing semantic structure.")

            if not any(token in css for token in ["@media", "grid", "flex"]):
                soft.append(f"Page {idx + 1} CSS may lack responsive/layout constructs.")

            for marker in generic_markers:
                if marker in html:
                    soft.append(f"Page {idx + 1} contains generic placeholder copy ('{marker}').")
                    break

            # Prevent direct prompt-dump behavior.
            prompt_words = [w for w in prompt_lower.split() if len(w) > 4]
            if prompt_words:
                overlap = sum(1 for w in prompt_words if w in html)
                overlap_ratio = overlap / max(1, len(prompt_words))
                threshold = 0.70 if strictness == "high" else 0.78
                if overlap_ratio > threshold:
                    soft.append(f"Page {idx + 1} appears to mirror prompt text too closely.")

        return {"critical": critical, "soft": soft}

    def _generate_fallback(self, prompt: str, style: str, pages: int, reason: str = "") -> Dict[str, Any]:
        generated_pages = []
        for idx in range(pages):
            page_name = "Home" if idx == 0 else f"Page {idx + 1}"
            generated_pages.append(
                {
                    "name": page_name,
                    "html": self._fallback_html(style, page_name),
                    "css": self._fallback_css(style),
                    "js": self._fallback_js(page_name),
                }
            )

        return {
            "title": "Fallback Generated Website",
            "summary": "Generated without live model output. Configure provider key to enable AI generation.",
            "pages": generated_pages,
            "source": "fallback",
            "reason": reason or "Live model unavailable.",
        }

    def _normalize_page(self, page: Dict[str, Any], idx: int) -> Dict[str, str]:
        return {
            "name": (page or {}).get("name") or f"Page {idx + 1}",
            "html": (page or {}).get("html") or "<main><h1>Untitled</h1></main>",
            "css": (page or {}).get("css") or "",
            "js": (page or {}).get("js") or "",
        }

    def _fallback_html(self, style: str, page_name: str) -> str:
        safe_style = style.replace("<", "&lt;").replace(">", "&gt;")
        safe_page = page_name.replace("<", "&lt;").replace(">", "&gt;")

        return f"""<main class=\"layout\">\n  <header class=\"hero\">\n    <p class=\"eyebrow\">{safe_style}</p>\n    <h1>{safe_page}</h1>\n    <p>A starter page was generated. Enable live model access for prompt-aware AI composition.</p>\n    <button id=\"ctaBtn\" class=\"btn\">Start Experience</button>\n  </header>\n\n  <section class=\"grid\" aria-label=\"Feature list\">\n    <article class=\"card\"><h2>Fast Build</h2><p>Generated structure with responsive foundations.</p></article>\n    <article class=\"card\"><h2>Accessible</h2><p>Semantic sections and keyboard-friendly controls.</p></article>\n    <article class=\"card\"><h2>Customizable</h2><p>Edit code blocks instantly after generation.</p></article>\n  </section>\n</main>"""

    def _fallback_css(self, style: str) -> str:
        return """* { box-sizing: border-box; }\n:root {\n  --bg: #f4f9fb;\n  --surface: #ffffff;\n  --text: #0f172a;\n  --muted: #475569;\n  --brand: #0ea5a4;\n}\nbody { margin: 0; font-family: 'Manrope', 'Segoe UI', sans-serif; background: radial-gradient(circle at 0 0, #dff4f7 0%, var(--bg) 45%); color: var(--text); }\n.layout { max-width: 1120px; margin: 0 auto; padding: 2rem 1rem 4rem; }\n.hero { background: var(--surface); border: 1px solid #d9e7ee; border-radius: 24px; padding: 2rem; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08); }\n.eyebrow { display: inline-block; border-radius: 999px; background: #ecfeff; color: #155e75; padding: 0.3rem 0.8rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; }\n.btn { margin-top: 1rem; border: 0; border-radius: 12px; background: var(--brand); color: #fff; padding: 0.75rem 1rem; font-weight: 700; cursor: pointer; }\n.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin-top: 1.25rem; }\n.card { background: var(--surface); border-radius: 18px; border: 1px solid #d9e7ee; padding: 1rem; }\n@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }\n"""

    def _fallback_js(self, page_name: str) -> str:
        return f"""document.addEventListener('DOMContentLoaded', () => {{\n  const cta = document.getElementById('ctaBtn');\n  if (!cta) return;\n  cta.addEventListener('click', () => {{\n    alert('Launching {page_name}');\n  }});\n}});\n"""

    def _parse_json_payload(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("Model output was not valid JSON.")
            return json.loads(text[start : end + 1])
