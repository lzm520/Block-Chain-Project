from ecdsa import SigningKey, VerifyingKey, BadSignatureError


# 创建账号私钥和公钥
def gen_private_public_key():
    # 私钥
    sk = SigningKey.generate()
    sk_string = sk.to_string().hex()
    print(sk_string)
    # 公钥
    vk = sk.get_verifying_key()
    vk_string = vk.to_string().hex()
    print(vk_string)


# 创建题目，用于交易验证
def gen_puzzle(private_key, raw_msg='HelloWorld'):
    sk = SigningKey.from_string(bytes.fromhex(private_key))
    encrypt_msg = sk.sign(str.encode(raw_msg)).hex()
    return encrypt_msg, raw_msg


if __name__ == '__main__':
    encrypt_msg, raw_msg = gen_puzzle('397032c15155d94f63f13dcb893ccc5cddc8520c0185e8bf')
    print(encrypt_msg)
    print(bytes.fromhex(encrypt_msg))
    print(raw_msg)
    # address = '3ad26e7610e7fb4d1434a4b774d8b2c100827bd3c6ae0cd515242aa449065f914d5952fd9ff838bc1960c25d322ec50a'
    address = 'fe0fb61c468138a9d3f7e13bb50115dddb000c6a6e2a03f7391f557264d4eda8feecfc9619c527f26ac48a00778902e7'
    public_key = VerifyingKey.from_string(bytes.fromhex(address))
    try:
        verify = public_key.verify(bytes.fromhex(encrypt_msg), str.encode(raw_msg))
    except BadSignatureError:
        verify = False
    print(verify)