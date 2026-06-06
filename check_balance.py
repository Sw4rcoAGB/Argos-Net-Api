from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://sepolia.drpc.org"))
addr = "0x6782002cce06d409D86124C1ef640A647bdAd128"
bal = w3.eth.get_balance(addr)
gp = w3.eth.gas_price
cost = 2_500_000 * gp
print(f"Balance: {w3.from_wei(bal, 'ether')} ETH")
print(f"Gas price: {w3.from_wei(gp, 'gwei')} gwei")
print(f"Costo estimado (2.5M gas): {w3.from_wei(cost, 'ether')} ETH")
print(f"Suficiente: {bal > cost}")
