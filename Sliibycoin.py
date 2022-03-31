import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request
from ecdsa import VerifyingKey,BadSignatureError


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.block_generation_interval = 10
        self.difficulty_adjustment_interval = 10
        
        
        # Create the genesis block
        self.new_genesis_block()

    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = last_block['hash']
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(block, block['difficulty']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False
    
    def new_genesis_block(self):
        block = {
            'index': 1,
            'hash': "1",
            'previous_hash': "0",
            'timestamp': time(),
            'transactions': [],
            'difficulty': 4,
            'nonce': 0,
        }
        return block
             
    def new_block(self):
        last_block = self.chain[-1]
        
        block = {
            'index': last_block['index'] + 1,
            'previous_hash': last_block['hash'],
            'timestamp': time(),
            'transactions': self.current_transactions,
        }
        
        block['hash'] = self.hash(block)
        block['difficulty'] = self.get_difficulty()
        block['nonce'] = 0
        block['nonce'] = self.proof_of_work(block)
        
        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block
    
    
    def get_difficulty(self):
        last_block = self.last_block()
        if (last_block.index % self.block_generation_interval == 0):
            prev_adjustment_block = self.chain[len(self.chain) - self.difficulty_adjustment_interval]
            time_expected = self.block_generation_interval * self.difficulty_adjustment_interval
            time_taken = last_block.timestamp - prev_adjustment_block.timestamp
            
            if (time_taken < time_expected / 2):
                return prev_adjustment_block.difficulty + 1
            else:
                if (time_expected > time_expected * 2):
                    return prev_adjustment_block.difficulty - 1
                else: 
                    return prev_adjustment_block.difficulty
        else:
            return last_block.difficuly
    
    
    def proof_of_work(self, block):
        nonce = 0
        difficulty = block['difficulty']
        header_hash = self.hash(block)
        while self.valid_proof(header_hash, difficulty) is False:
            nonce += 1
            block['nonce'] = nonce
            header_hash = self.hash(block)

        return nonce

    @staticmethod
    def valid_proof(header_hash, difficulty):
        prefix_target = "0000000000"[0:difficulty]
        guess = f'{header_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == prefix_target
            

    # 创建新交易
    def new_transaction(self, values, coinBase=False):
        # Adds a new transaction to the list of transactions(向交易列表中添加一个新的交易)
        """
                生成新交易信息，此交易信息将加入到下一个待挖的区块中
                :param coinBase: 判断新加入的transaction是不是从coinBase产生的
                :param values:
        """
        hash_string = json.dumps(values, sort_keys=True).encode()
        transaction_id = hashlib.sha256(hash_string).hexdigest()
        if coinBase:
            self.currentTransaction.insert(0, {
                'id': transaction_id,
                'txIns': values['txIns'],
                'txOut': values['txOut'],
            })
            for transaction in self.currentTransaction:
                for tx_out in transaction['txOut']:
                    if tx_out['address'] == '-999':
                        tx_out['address'] = values['txOut'][0]['address']
        else:
            self.currentTransaction.append({
                'id': transaction_id,
                'txIns': values['txIns'],
                'txOut': values['txOut'],
            })

        return self.last_block['index'] + 1

    def transaction_validation(self, tx_in):
        for block in self.chain:
            for transaction in block['transactions']:
                if tx_in['txOutId'] == transaction['id']:
                    pre_tx_outs = transaction['txOut']
                    # 判断输入的索引没有没问题
                    if tx_in['txOutIndex'] >= len(pre_tx_outs):
                        print(len(pre_tx_outs))
                        print(tx_in['txOutIndex'])
                        return False, 'Index gets error', 0
                    pre_tx_out = pre_tx_outs[tx_in['txOutIndex']]
                    # 判断输出的address和输入的signature能否验证
                    public_key = VerifyingKey.from_string(bytes.fromhex(pre_tx_out['address']))
                    encrypt_msg = bytes.fromhex(tx_in['signature']['encryptMsg'])
                    raw_msg = tx_in['signature']['rawMsg']
                    try:
                        verify = public_key.verify(encrypt_msg, str.encode(raw_msg))
                    except BadSignatureError:
                        verify = False
                    if verify:
                        return True, 'Successfully', pre_tx_out['amount']
                    else:
                        return True, 'Decryption error', pre_tx_out['amount']
        return False, "Don't find specific txOutId", 0

    @staticmethod
    def hash(block):
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()



# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()
 
 
# 创建 /transactions/new 端点，这是一个 POST 请求，我们将用它来发送数据
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    """
    输入数据格式：
    values = {
        "txIns": [
            {
                "txOutId": String,
                "txOutIndex": Number,
                "signature": {
                    "encryptMsg": String,
                    "rawMsg": String
                }
            },
        ],
        "txOut": [
            {
                "address": String,
                "amount": Number
            },
        ]
    }
    """
    # 将请求参数做了处理，得到的是字典格式的，因此排序会打乱依据字典排序规则
    values = request.get_json()
 
    # 检查所需字段是否在过账数据中
    required = ['txIns', 'txOut']
    if not all(k in values.keys() for k in required):
        return 'Missing values', 400  # HTTP状态码等于400表示请求错误
    # 检测交易输入数据结构
    tx_ins = values['txIns']
    if type(tx_ins == list):
        tx_in_required = ['txOutId', 'txOutIndex', 'signature']
        for tx_in in tx_ins:
            if not all(k in tx_in.keys() for k in tx_in_required):
                return 'Missing values', 400
            signature_required = ['encryptMsg', 'rawMsg']
            if not all(k in tx_in['signature'].keys() for k in signature_required):
                return 'Missing values', 400
    else:
        return 'Submission structure is error', 400
    # 检测交易输出数据结构
    tx_outs = values['txOut']
    if type(tx_outs == list):
        tx_out_required = ['address', 'amount']
        for tx_out in tx_outs:
            if not all(k in tx_out.keys() for k in tx_out_required):
                return 'Missing values', 400
    else:
        return 'Submission structure is error', 400

    # todo：1、检查txIns里面的所有订单号是否存在；2、订单检测private-public key；3、统计所有的coin ammount；
    in_coin_amount = 0
    for tx_in in tx_ins:
        flag, msg, amount = blockchain.transaction_validation(tx_in)
        if not flag:
            return 'Transactions validation failed: ' + msg, 400
        in_coin_amount += float(amount)
    # todo：1、统计输出的coin数量，多于coin amount则出错，少于则发送给挖币人员。
    out_coin_amount = 0
    for tx_out in tx_outs:
        out_coin_amount += float(tx_out['amount'])
    if out_coin_amount > in_coin_amount:
        return 'Output coin is larger than Input coin', 400
    if out_coin_amount < in_coin_amount:
        values['txOut'].append(
            {
                'address': '-999',
                'amount': in_coin_amount - out_coin_amount
            }
        )
    # 创建新交易
    index = blockchain.new_transaction(values)
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201
 
 
# 创建 /mine 端点，这是一个GET请求
@app.route('/mine', methods=['GET'])
def mine():
    # 我们运行工作证明算法来获得下一个证明
    last_block = blockchain.last_block  # 取出区块链现在的最后一个区块
    last_proof = last_block['proof']  # 取出这最后 一个区块的哈希值（散列值）
    proof = blockchain.proof_of_work(last_proof)  # 获得了一个可以实现优先创建（挖出）下一个区块的工作量证明的proof值。
 
    # 由于找到了证据，我们会收到一份奖励
    # txIn为空列表，表示此节点已挖掘了一个新货币
    address = request.args.get("address")
    values = {
        'txIns': [],
        'txOut': [{
            'address': address,
            'amount': 50
        }]
    }
    blockchain.new_transaction(values, True)
 
    # 将新块添加到链中打造新的区块
    previous_hash = blockchain.hash(last_block)  # 取出当前区块链中最长链的最后一个区块的Hash值，用作要新加入区块的前导HASH（用于连接）
    block = blockchain.new_block(proof, previous_hash)  # 将新区快添加到区块链最后
 
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'nonce': block['nonce'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201




@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
