import os
import sys

# Ajouter src/ au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dotenv import load_dotenv

from aegis_trade.domain import Symbol, AssetClass, TimeFrame
from aegis_trade.providers.mt5_provider import MT5Provider
from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.engine import DatasetEngine
from datetime import datetime, timedelta

import argparse

def main():
    parser = argparse.ArgumentParser(description="Ingest MT5 market data.")
    parser.add_argument("--symbols", nargs="+", default=["XAUUSD", "EURUSD"], help="List of symbols to ingest")
    parser.add_argument("--timeframe", type=str, default="H1", help="Timeframe (e.g., H1, M15)")
    parser.add_argument("--days", type=int, default=730, help="Number of days of history to fetch")
    args = parser.parse_args()

    print("--- Démarrage du Pipeline d'Ingestion MT5 ---")
    
    # Charger les variables d'environnement (.env)
    load_dotenv()
    
    # 1. Initialisation du provider
    print("Connexion au terminal MetaTrader 5...")
    provider = MT5Provider()
    status = provider.health_check()
    if not status.connected:
        print(f"[ERROR] Echec de la connexion MT5 : {status.last_error}")
        print("Vérifiez que MT5 est ouvert et que les identifiants dans le fichier .env sont corrects.")
        return
        
    print(f"[SUCCESS] MT5 Connecte (Latence: {status.latency:.4f}s)")
    
    # 2. Initialisation du Dataset Engine
    # Le stockage se fera dans le dossier 'data/datasets' à la racine du projet
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root_dir, "data", "datasets")
    
    repository = StorageDatasetRepository(storage=data_dir)
    engine = DatasetEngine(repository=repository)
    
    # 3. Définition des cibles
    # Default asset class mapping (simplified)
    def guess_asset_class(sym: str) -> AssetClass:
        return AssetClass.FOREX if "USD" in sym and sym != "XAUUSD" else AssetClass.COMMODITIES

    targets = [Symbol(name=s, asset_class=guess_asset_class(s)) for s in args.symbols]
    
    timeframe = TimeFrame(args.timeframe)
    date_to = datetime.now()
    date_from = date_to - timedelta(days=args.days)
    
    # 4. Boucle d'Ingestion
    for symbol in targets:
        print(f"\n[ {symbol.name} | {timeframe.value} ]")
        try:
            print(f"  -> Téléchargement de l'historique du {date_from.date()} au {date_to.date()}...")
            bars = provider.get_bars_range(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
            print(f"  -> {len(bars)} barres récupérées et normalisées.")
            
            print("  -> Validation et Ingestion dans l'Event Store / Storage...")
            dataset = engine.ingest_market_bars(
                bars=bars,
                provider="mt5",
                provider_version="1.0"
            )
            
            print(f"  [SUCCESS] Succes ! Dataset persistant genere.")
            print(f"     - Hash: {dataset.dataset_hash}")
            print(f"     - Début: {dataset.date_start}")
            print(f"     - Fin: {dataset.date_end}")
            print(f"     - Lignes: {dataset.row_count}")
            
        except Exception as e:
            print(f"  [ERROR] Erreur critique sur {symbol.name} : {e}")

    print("\n--- Pipeline terminé ---")

if __name__ == "__main__":
    main()
