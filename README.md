# binance-analisys

## Docker

1. Crie um arquivo `.env` na raiz do projeto com as variáveis necessárias (por exemplo, chaves da API da Binance).
2. Construa a imagem Docker:

   ```bash
   docker build -t binance-analisys .
   ```

3. Execute o container carregando as variáveis do `.env` e expondo a porta do Streamlit:

   ```bash
   docker run --env-file .env -p 8501:8501 binance-analisys
   ```

O painel estará disponível em `http://localhost:8501`.
