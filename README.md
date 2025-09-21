# Solana 靓号生成器

本项目是一个基于 Python 的 Solana 靓号地址生成器，支持助记词模式（可恢复钱包）和私钥模式（更快）。  
可以自定义前缀和后缀（严格区分大小写），支持多线程加速，也可以打包为独立可执行文件方便使用。

## 使用方法

按提示输入前缀、后缀、生成数量和线程数，例如输入 prefix=00，suffix=8888，count=1，threads=8。

生成的文件会在 当前文件夹中。

此程序可以全程断网运行。

依赖
solders, mnemonic, base58

免责声明
本工具仅供学习与个人使用，请妥善保管私钥与助记词，因使用本工具造成的任何资产损失，作者概不负责。


# Solana Vanity Address Generator

This project is a Python-based Solana vanity address generator, supporting mnemonic mode (recoverable wallet) and private key mode (faster).  
You can customize prefix and suffix (case-sensitive), use multi-threading to accelerate, and optionally package it as a standalone executable for convenience.

## Usage

Follow the prompts to input prefix, suffix, number of addresses, and thread count.  
For example: prefix=00, suffix=8888, count=1, threads=8.

The generated file will be saved in the current folder.

This program can run completely offline.

Dependencies  
solders, mnemonic, base58

Disclaimer  
This tool is for learning and personal use only. Please keep your private keys and mnemonics safe. The author is not responsible for any asset loss caused by using this tool.
