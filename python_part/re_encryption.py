from umbral import config
from umbral.curve import SECP256K1
from umbral import keys, signing
from umbral import pre
import base64
import pickle
import ast

config.set_default_curve(SECP256K1)


class ReEncryption:

    def generateKeys(account) -> str:
        private_key = keys.UmbralPrivateKey.gen_key()
        public_key = private_key.get_pubkey()
        signing_key = keys.UmbralPrivateKey.gen_key()
        verifying_key = signing_key.gen_key()
        pub_res = {}
        pri_res = {}
        pri_res['private_key'] = private_key.to_bytes()
        pri_res['signing_key'] = signing_key.to_bytes()

        pub_res['public_key'] = public_key.to_bytes()
        pub_res['verifying_key'] = verifying_key.to_bytes()
        with open(account + '_privacy', 'wb') as file:
            pickle.dump(pri_res, file)
        return pub_res.__str__()

    def encryptInfo(account: str, access_pub_key_bytes) -> str:
        with open('example.jpeg', 'rb') as f:
            img = base64.b64encode(f.read())
            f.close()
        with open(account + '_privacy', 'rb') as f:
            user_info_bytes = pickle.load(f)
            f.close()
        access_pub_key = keys.UmbralPublicKey.from_bytes(access_pub_key_bytes)
        owner_pri_key = keys.UmbralPrivateKey.from_bytes(user_info_bytes['private_key'])
        owner_signing_key = keys.UmbralPrivateKey.from_bytes(user_info_bytes['signing_key'])
        owner_pub_key = owner_pri_key.get_pubkey()
        ciphertext, capsule = pre.encrypt(owner_pub_key, img)
        signer = signing.Signer(private_key=owner_signing_key)
        kfrags = pre.generate_kfrags(delegating_privkey=owner_pri_key,
                                     signer=signer,
                                     receiving_pubkey=access_pub_key,
                                     threshold=1,
                                     N=2)
        res = {}
        res['ciphertext'] = ciphertext
        res['capsule'] = capsule.to_bytes()
        bytes_kfrags = list()
        for v in kfrags:
            bytes_kfrags.append(v.to_bytes())
        res['kfrags'] = bytes_kfrags
        return res.__str__()

    def reencryption(a_pub_key_bytes, a_ver_key_bytes, b_pub_key_bytes, kfrags_bytes, capsule_bytes):
        kfrags = list()
        for v in kfrags_bytes:
            kfrag = pre.KFrag.from_bytes(v)
            kfrags.append(kfrag)
        a_pub_key = keys.UmbralPublicKey.from_bytes(a_pub_key_bytes)
        a_ver_key = keys.UmbralPublicKey.from_bytes(a_ver_key_bytes)
        b_pub_key = keys.UmbralPublicKey.from_bytes(b_pub_key_bytes)
        capsule = pre.Capsule.from_bytes(capsule_bytes, a_pub_key.params)
        capsule.set_correctness_keys(delegating=a_pub_key,
                                     receiving=b_pub_key,
                                     verifying=a_ver_key)
        cfrags_bytes = list()
        for kfrag in kfrags:
            cfrag = pre.reencrypt(kfrag=kfrag, capsule=capsule)
            cfrags_bytes.append(cfrag.to_bytes())
        return cfrags_bytes

    def decrypt(account, a_pub_key, a_ver_key, ciphertext, cfrags_bytes, capsule_bytes):
        with open(account + '_privacy', 'rb') as f:
            user_info_bytes = pickle.load(f)
            f.close()
        pri_key = keys.UmbralPrivateKey.from_bytes(user_info_bytes['private_key'])
        pub_key = pri_key.get_pubkey()
        capsule = pre.Capsule.from_bytes(capsule_bytes, pub_key.params)
        capsule.set_correctness_keys(delegating=a_pub_key, receiving=pub_key, verifying=a_ver_key)
        cfrags = list()
        for cfrag_bytes in cfrags_bytes:
            cfrag = pre.CapsuleFrag.from_bytes(cfrag_bytes)
            cfrags.append(cfrag)
        for cfrag in cfrags:
            capsule.attach_cfrag(cfrag)
        img_bytes = pre.decrypt(ciphertext=ciphertext,
                                capsule=capsule,
                                decrypting_key=pri_key)
        img = base64.b64decode(img_bytes)
        return img


# ReEncryption.generateKeys('Alice')
# ReEncryption.generateKeys('Bob')

with open('Alice_privacy', 'rb') as f:
    alice = pickle.load(f)
    f.close()
with open('Bob_privacy', 'rb') as f:
    bob = pickle.load(f)
    f.close()

alice_private_key = keys.UmbralPrivateKey.from_bytes(alice['private_key'])
alice_public_key = alice_private_key.get_pubkey()
alice_signing_key = keys.UmbralPrivateKey.from_bytes(alice['signing_key'])
alice_verifying_key = alice_signing_key.get_pubkey()

bob_private_key = keys.UmbralPrivateKey.from_bytes(bob['private_key'])
bob_public_key = bob_private_key.get_pubkey()
bob_signing_key = keys.UmbralPrivateKey.from_bytes(bob['signing_key'])
bob_verifying_key = bob_signing_key.get_pubkey()

info = ReEncryption.encryptInfo('Alice', bob_public_key.to_bytes())
dict = ast.literal_eval(info)
ciphertext, capsule_bytes, kfrags_bytes = dict['ciphertext'], dict['capsule'], dict['kfrags']
print(ciphertext)
print(capsule_bytes)
print(kfrags_bytes)

cfrags_bytes = ReEncryption.reencryption(alice_public_key.to_bytes(), alice_verifying_key.to_bytes(),
                                         bob_public_key.to_bytes(), kfrags_bytes, capsule_bytes)
print(cfrags_bytes)

img = ReEncryption.decrypt('Bob', alice_public_key, alice_verifying_key, ciphertext, cfrags_bytes, capsule_bytes)
with open('return_example.jpeg', 'wb') as f:
    f.write(img)
    f.close()
