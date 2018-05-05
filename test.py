#!/usr/bin/env python3

from pyhy import *
import sys
import binascii

TEST_CTX = 'test1234'
FAIL_CTX = '1234test'
INVALID_CTX = '123456789'
STATIC_MASTER_KEY = bytes(b'\x82\xb8\x22\x0b\x8b\xb1\xf3\x2b\x63\x68\x9c\xca\x0f\x73\x86\xc3\x7a\x09\xbf\x76\xbd\x66\xf0\xca\x40\x17\x62\x94\x7a\x93\x92\x22')


################################################################################
# rand - TODO better tests
################################################################################
MAX_U32 = 2**32
MAX_U64 = 2**64

def assert_u32(n):
    assert (n >= 0) and (n < MAX_U32), 'got invalid u32 %d' % n

def test_rand():
    n = hydro_random_u32()
    assert_u32(n)
    assert (n >= 0) and (n < MAX_U32), 'got invalid u32 %d' % n
    for i in range(1, 128):
        n = hydro_random_uniform(i)
        assert_u32(n)
    nbuf = hydro_random_buf( hydro_random_SEED )
    assert len(nbuf) == hydro_random_SEED
    dbuf = hydro_random_buf_deterministic(1234, nbuf)
    assert len(dbuf) == 1234

    # nbuf = hydro_random_buf(i, seed)
    hydro_random_ratchet()
    hydro_random_reseed()

################################################################################
# hash - TODO: min/max outlen for hash_ash
################################################################################
def test_hash():
    hkey = hydro_hash_keygen()
    print('hash_keygen:', hkey.hex())
    hash = hydro_hash_hash(hydro_hash_BYTES*2, 'Arbitrary data to hash', TEST_CTX, hkey)
    print('hash_hash:', hash.hex())
    hash = hydro_hash_hash(hydro_hash_BYTES*2, 'Arbitrary data to hash', TEST_CTX)
    print('hash_hash (no key):', hash.hex())

    h1 = hydro_hash(TEST_CTX, hkey)
    h1.update('some data')
    h1.update('more data')
    h1hash = h1.final()
    # print('h1hash:', h1hash.hex())
    h2 = hydro_hash(TEST_CTX, hkey)
    h2.update('some data')
    h2.update('more data')
    h2hash = h2.final()
    assert h1hash == h2hash
    print('h1hash == h2hash')


################################################################################
# kdf
################################################################################
def test_kdf():
    print('\ntest_kdf')
    master_key = hydro_kdf_master_keygen()
    assert len(master_key) == 32
    bad_master_key = hydro_kdf_master_keygen()
    # print('Master key:', master_key.hex())
    subkey1 = hydro_kdf_derive_from_key(16, 0, TEST_CTX, master_key)
    assert len(subkey1) == 16
    subkey2 = hydro_kdf_derive_from_key(16, 0, TEST_CTX, master_key)
    assert subkey1 == subkey2
    subkey2 = hydro_kdf_derive_from_key(16, 0, FAIL_CTX, master_key)
    assert subkey1 != subkey2
    subkey2 = hydro_kdf_derive_from_key(16, 1, TEST_CTX, master_key)
    assert subkey1 != subkey2
    subkey2 = hydro_kdf_derive_from_key(16, 0, TEST_CTX, bad_master_key)
    assert subkey1 != subkey2
    subkey2 = hydro_kdf_derive_from_key(32, 0, TEST_CTX, master_key)
    assert subkey1 != subkey2
    assert len(subkey2) == 32
    bunch_of_subkeys = []
    for i in range(0, 1024):
        subkey_n = hydro_kdf_derive_from_key(16, i, TEST_CTX, master_key)
        assert subkey_n not in bunch_of_subkeys
        bunch_of_subkeys.append(subkey_n)
    subkey1_again = hydro_kdf_derive_from_key(16, 0, TEST_CTX, master_key)
    assert subkey1 == subkey1_again
    return

################################################################################
# Secretbox
################################################################################
TEST_TEXT = 'This is a test'
FAIL_TEXT = 'This is not a test'

def assert_plaintext(ptxt, check_txt):
    if (ptxt is None) or (ptxt.decode() != check_txt):
        raise Exception('failed to decrypt')
    print('Decrypted plaintext: ', ptxt)

def test_secretbox():
    print('\ntest_secretbox')
    goodkey = hydro_secretbox_keygen()
    # print('Generated key:', key.hex())
    ctxt = hydro_secretbox_encrypt(TEST_TEXT, 0, TEST_CTX, goodkey)
    # print('Ciphertext: ', ctxt.hex())
    #### pass case
    ptxt = hydro_secretbox_decrypt(ctxt, 0, TEST_CTX, goodkey)
    assert_plaintext(ptxt, TEST_TEXT)
    #### some fail cases
    badkey = hydro_secretbox_keygen()
    ptxt = hydro_secretbox_decrypt(ctxt, 0, TEST_CTX, badkey)
    assert ptxt is None, 'ptxt should be None'
    ptxt = hydro_secretbox_decrypt(ctxt, 0, FAIL_CTX, goodkey)
    assert ptxt is None, 'ptxt should be None'
    return

def test_secretbox_probes():
    print('\ntest_secretbox_probes')
    key = hydro_secretbox_keygen()
    ctxt = hydro_secretbox_encrypt('This is a test', 0, TEST_CTX, key)
    probe = hydro_secretbox_probe_create(ctxt, TEST_CTX, key)
    # print('Generated probe:', probe.hex())
    assert hydro_secretbox_probe_verify(probe, ctxt, TEST_CTX, key) == True, 'probe verification failed'
    print('probe verified')

################################################################################
# Sign
################################################################################
def test_signature_pass():
    print('\ntest_signature')
    kp = hydro_sign_keygen()
    ss1 = hydro_sign(TEST_CTX)
    ss1.update('first chunk')
    ss1.update('second chunk')
    sig = ss1.final_create(kp.sk)
    # print('Signature: ', sig.hex())

    ss2 = hydro_sign(TEST_CTX)
    ss2.update('first chunk')
    ss2.update('second chunk')
    assert ss2.final_verify(sig, kp.pk) == True, 'signature verification failed'
    print('OK: signature verified')

def test_signature_fail():
    print('\ntest_signature_fail')
    kp = hydro_sign_keygen()
    ss1 = hydro_sign(TEST_CTX)
    ss1.update('first chunk')
    ss1.update('second chunk')
    sig = ss1.final_create(kp.sk)
    # print('Signature: ', sig.hex())

    ss2 = hydro_sign(TEST_CTX)
    ss2.update('first chunk')
    ss2.update('second chunk')
    ss2.update('third chunk weeeee')
    assert ss2.final_verify(sig, kp.sk) == False, 'signature verification should have failed'
    print('OK: signature verification failed')

def test_sign_readme():
    YOUR_CTX = 'context1'
    kp = hydro_sign_keygen()
    s1 = hydro_sign(YOUR_CTX)
    s1.update('first chunk')
    s1.update('second chunk')
    sig = s1.final_create(kp.sk)
    print('Signature: ', sig.hex())

    s2 = hydro_sign(YOUR_CTX)
    s2.update('first chunk')
    s2.update('second chunk')
    assert s2.final_verify(sig, kp.pk) == True

################################################################################
# kx - TODO
################################################################################


################################################################################
# pwhash
################################################################################
TEST_PW = 'shittypassword'
TEST_PW_CTX = 'password'

def test_pwhash():
    print('\ntest_pwhash')
    master_key = hydro_pwhash_keygen()
    # print('pwhash master_key:', master_key.hex() )
    pwkey = hydro_pwhash_deterministic(TEST_PW, TEST_PW_CTX, master_key)
    print('pwhash for %s: %s' % (TEST_PW, pwkey.hex()))
    assert pwkey == hydro_pwhash_deterministic(TEST_PW, TEST_PW_CTX, master_key)

################################################################################
# other
################################################################################
def test_other():
    print('\ntest_other')
    # context integrity checks
    try: oops = hydro_sign(INVALID_CTX)
    except Exception as e: print('Bad ctx len assertion ok')
    try: oops = hydro_sign(1234)
    except Exception as e: print('Bad ctx type assertion ok')

def test_hexify():
    print('\ntest_hexify')
    YOUR_CTX = 'context1'
    # kp = hydro_sign_keygen()
    # dump_keypair_hex(kp)
    your_sk_hex = 'a3d8acb3055b370085a15a1357354545fe28f29933c38745e723cdacfdb0b1bf7e36d864be0145ded2912ceb05c0e66257e8db78e5eb0dd880345c842e7e1d1b'
    your_pk_hex = '7e36d864be0145ded2912ceb05c0e66257e8db78e5eb0dd880345c842e7e1d1b'
    s1 = hydro_sign(YOUR_CTX)
    s1.update('first chunk')
    s1.update('second chunk')
    sig = s1.final_create( unhexify(your_sk_hex) )
    print('Signature: ', sig.hex())

    s2 = hydro_sign(YOUR_CTX)
    s2.update('first chunk')
    s2.update('second chunk')
    assert s2.final_verify(sig, unhexify(your_pk_hex)) == True

    your_sig_hex = 'f6db10e2e9d91297c30db2df5a85aba99abcf57aaf0ca99a8f849582f756e81785e32d9f73d250b9492bb8e0d7ce07df5bbc3f1875b13e1c1473b5d59c38b606'
    s2 = hydro_sign(YOUR_CTX)
    s2.update('first chunk')
    s2.update('second chunk')
    assert s2.final_verify( unhexify(your_sig_hex), unhexify(your_pk_hex)) == True
    print('Hardcoded pk/sk/sig ok')

def test_helpers():
    import time
    print('\ntest_helpers')
    nbuf = hydro_random_buf( 32 )
    print('memzero before: %s' % nbuf.hex())
    hydro_memzero(nbuf, dump_loc=True)
    print( 'after location: %x' % id(nbuf) )
    print('memzero after: %s' % nbuf.hex())

    nbuf = hydro_random_buf( 32 )
    nbuf2 = hydro_random_buf( 32 )
    assert (hydro_equal(nbuf, nbuf2) == False)
    hydro_memzero(nbuf)
    hydro_memzero(nbuf2)
    assert (hydro_equal(nbuf, nbuf2) == True)
    assert (hydro_equal(nbuf, nbuf2, 32) == True)
    nbuf2 = hydro_random_buf( 10 )
    assert (hydro_equal(nbuf, nbuf2, 10) == False)
    assert (hydro_equal(nbuf, nbuf2, 512) == False)
    assert (hydro_equal('test1'.encode('utf8'), 'test2'.encode('utf8')) == False)
    assert (hydro_equal('test1'.encode('utf8'), 'test1'.encode('utf8')) == True)

    nbuf = hydro_random_buf( 4 )
    hydro_memzero(nbuf)
    for i in range(0, 2**12):
        hydro_increment(nbuf)
        sys.stdout.write( '\r%s\r' % nbuf.hex() )
        time.sleep(0.000001)
    print('\nnbuf final: %s\r' % nbuf.hex())
    assert nbuf.hex() == '00100000'

################################################################################
# Init
################################################################################

def main():
    # wrapper
    print( hydro_version() )
    print( pyhy_version() )
    # rand
    test_rand()
    # hash
    test_hash()
    # kdf
    test_kdf()
    # secretbox
    test_secretbox()
    test_secretbox_probes()
    # sign
    test_signature_pass()
    test_signature_fail()
    test_sign_readme()
    test_other()
    test_hexify()
    # kx - n
    # kx - kk
    # kx - xx
    # pwhash
    test_pwhash()
    # helpers
    test_helpers()
    return


if __name__ == '__main__':
    main()


sys.exit(0)
