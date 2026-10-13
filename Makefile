.PHONY: serve test unlock lock status

serve:
	cd site && python3 -m http.server 8000

test:
	python3 scripts/check_site.py

unlock:
	git-crypt unlock

lock:
	git-crypt lock

status:
	git-crypt status
