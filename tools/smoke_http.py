"""Run after starting python run.py; only probes localhost:5000.

Uses raw HTTP paths, so the percent-encoding examples are not
pre-encoded by a form or library.
"""
import http.client
import argparse

CASES = [
    ('/download?path=baocao.pdf', 200),
    ('/download?path=b%C3%A1o%20c%C3%A1o%20t%E1%BB%91t%20nghi%E1%BB%87p.pdf', 200),
    ('/download?path=tailieu%2Fchuong1.pdf', 200),
    ('/download?path=..%2Fsecret.txt', 403),
    ('/download?path=..%2F..%2Fconfig.txt', 403),
    ('/download?path=..%5Csecret.txt', 403),
    ('/download?path=%2e%2e%2fsecret.txt', 403),
    ('/download?path=%252e%252e%252fsecret.txt', 403),
    ('/download?path=%25252e%25252e%25252fsecret.txt', 403),
    ('/download?path=notfound.pdf', 404),
]


def main(port=5000):
    passed = 0
    for path, expect in CASES:
        con = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        try:
            con.request('GET', path)
            response = con.getresponse()
            result = response.status
            response.read()
            ok = result == expect
            print(f"{'PASS' if ok else 'FAIL'} HTTP {result} expected {expect}: {path}")
            passed += ok
        finally:
            con.close()
    print(f'{passed}/{len(CASES)} pass')
    if passed != len(CASES):
        raise SystemExit(1)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=5000)
    args=parser.parse_args()
    if not 1 <= args.port <= 65535:parser.error('Port must be 1-65535')
    main(args.port)
