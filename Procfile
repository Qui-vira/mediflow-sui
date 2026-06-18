web: gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 --keep-alive 5 --max-requests 1000 frontend.app:app
coordinator: python agents/coordinator.py
intake: python agents/intake.py
verification: python agents/verification.py
resource: python agents/resource.py
sui-web: SUI_MODE=true gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 --keep-alive 5 --max-requests 1000 frontend.app:app
