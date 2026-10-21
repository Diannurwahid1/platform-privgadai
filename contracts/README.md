# PrivGadai CollateralProofRegistry

Kontrak ini berjalan di **BNB Smart Chain Testnet (chain ID 97)**. Hanya `bytes32` referensi event yang diacak dengan HMAC dan digest snapshot bersalt yang disimpan on-chain. KTP, identitas nasabah, foto, lokasi, nomor segel, UUID internal, dan hash berkas mentah tetap off-chain.

Alamat pilot dan transaksi smoke test sintetis tercatat di [`deployments/bsc-testnet.json`](deployments/bsc-testnet.json).

Kontrak memiliki admin untuk pause/unpause dan pengelolaan role, registrar untuk mendaftarkan proof, idempotensi untuk digest identik, serta penolakan saat event yang sama dikirim dengan digest lain. Wallet nasabah tidak diperlukan. Ini adalah bukti integritas waktu pencatatan, **bukan** bukti bahwa barang fisik benar-benar berada di vault.

```powershell
npm ci
npx hardhat build
npx hardhat test nodejs
npx tsc --noEmit
```

Untuk deploy, gunakan **wallet khusus testnet** dengan tBNB dari faucet BNB Chain. Simpan `BSC_TESTNET_PRIVATE_KEY` hanya sebagai environment variable lokal atau secret manager. Skrip `node scripts/create-testnet-wallet.mjs` membuat wallet baru di `.env` yang diabaikan Git; jangan jalankan jika wallet sudah ada. Hardhat tidak membaca `.env` otomatis, jadi muat variabel itu ke proses sebelum menjalankan:

```powershell
$env:BSC_TESTNET_PRIVATE_KEY = (Get-Content .env | Select-String '^BSC_TESTNET_PRIVATE_KEY=').ToString().Split('=',2)[1]
npx hardhat run scripts/deploy.ts --network bscTestnet
Remove-Item Env:BSC_TESTNET_PRIVATE_KEY
```

Konfirmasi alamat kontrak di BscScan testnet dan set `PROOF_CONTRACT_ADDRESS`, `PROOF_RELAYER_PRIVATE_KEY`, serta `PROOF_DIGEST_SECRET` pada backend. Aktifkan `PROOF_CHAIN_ENABLED=true` setelah relayer didanai. Jalankan `python -m dogeapi.proof.worker` sebagai proses backend terpisah. Jangan masukkan kunci privat atau salt ke frontend, log, Git, atau transaksi.
