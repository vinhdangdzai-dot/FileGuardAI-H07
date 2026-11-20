"""Run the existing localhost app with a hidden, process-only Gemini key prompt."""
import os
from pathlib import Path
import runpy
import sys
import getpass

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.verify_gemini_live import read_configuration
from app.ai_explanations import GeminiProvider,GeminiNativeProvider


def main():
    original=os.environ.get('AI_EXPLANATION_API_KEY')
    try:
        missing=not os.environ.get('AI_EXPLANATION_API_KEY') or not os.environ.get('AI_EXPLANATION_MODEL')
        read_configuration(prompt=missing and sys.stdin.isatty())
        key=os.environ.get('AI_EXPLANATION_API_KEY');model=os.environ.get('AI_EXPLANATION_MODEL')
        if not key or not model:
            print('NOT_RUN: configure environment or run in an interactive VS Code terminal.')
            return 2
        name=os.environ.get('AI_EXPLANATION_PROVIDER','gemini')
        provider_class=GeminiNativeProvider if name=='gemini-native' else GeminiProvider
        provider_class(key,model,os.environ.get('AI_EXPLANATION_TIMEOUT','20'),max_tokens=os.environ.get('AI_EXPLANATION_MAX_TOKENS','2048'))
        os.environ['AI_EXPLANATION_PROVIDER']='gemini-native' if name=='gemini-native' else 'gemini'
        print('Gemini adapter configured. Admin controls whether explanations are enabled.')
        runpy.run_path(str(ROOT/'run.py'),run_name='__main__')
        return 0
    except (ValueError,TypeError,getpass.GetPassWarning,EOFError):
        print('NOT_RUN: invalid configuration or secure terminal unavailable. No key was saved.')
        return 2
    except KeyboardInterrupt:return 130
    finally:
        if original is None:os.environ.pop('AI_EXPLANATION_API_KEY',None)


if __name__=='__main__':raise SystemExit(main())
