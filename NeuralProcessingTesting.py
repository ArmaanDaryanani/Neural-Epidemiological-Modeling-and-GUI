import tensorflow as tf
import numpy as np
from datetime import timedelta, datetime

import joblib
from CaseProcessing import CaseProcessing



class NeuralProcessingTesting:
    def __init__(self):
        self.processor = CaseProcessing("total_deaths.txt")
        self.look_back = 1
        self.scaler = None
        self.model = None

    def load_model_and_scaler(self):
        if self.model is None:
            self.model = tf.keras.models.load_model('deaths_model')
        if self.scaler is None:
            self.scaler = joblib.load('scaler.gz')

    def get_total_dict(self, days_passed):
        startdate = "2020-01-03"
        start_date = datetime.strptime(startdate, '%Y-%m-%d')
        final_date = start_date + timedelta(days=days_passed)
        year, month, day = final_date.year, final_date.month, final_date.day

        # Get the dictionary of country deaths
        country_deaths = self.processor.get_country_deaths_dict(day, month, year)

        # Exclude unnecessary indices
        country_deaths_cleaned = self.processor.exclude_indexes(country_deaths)

        return country_deaths_cleaned

    def get_total_list(self, days_passed):
        startdate = "2020-01-03"
        start_date = datetime.strptime(startdate, '%Y-%m-%d')
        final_date = start_date + timedelta(days=days_passed)
        year, month, day = final_date.year, final_date.month, final_date.day
        death_list = self.processor.exclude_indexes(self.processor.get_country_deaths_dict(day, month, year), True)
        death_list.insert(0, days_passed)
        return death_list

    def prepare_dataset(self, dataset):
        X, Y = [], []
        for i in range(len(dataset) - self.look_back):
            X.append(dataset[i:(i + self.look_back)])
            Y.append(dataset[i + self.look_back])
        return np.array(X), np.array(Y)

    def run_network(self):
        total_days = 1360
        dataset = [self.get_total_list(i) for i in range(total_days + 1)]
        dataset = self.scaler.fit_transform(dataset)

        X, Y = self.prepare_dataset(dataset)
        X = X.reshape(X.shape[0], self.look_back, -1)

        train_size = int(len(X) * 0.8)
        X_train, X_validate = X[:train_size], X[train_size:]
        Y_train, Y_validate = Y[:train_size], Y[train_size:]

        """MODEL"""
        my_model = tf.keras.models.Sequential()
        my_model.add(tf.keras.layers.LSTM(128, return_sequences=True, input_shape=(self.look_back, len(self.get_total_list(1)))))
        my_model.add(tf.keras.layers.Dropout(0.2))
        my_model.add(tf.keras.layers.LSTM(64, return_sequences=True))
        my_model.add(tf.keras.layers.Dropout(0.2))
        my_model.add(tf.keras.layers.LSTM(32))
        my_model.add(tf.keras.layers.Dense(len(self.get_total_list(1))))
        my_model.compile(optimizer='adam', loss='mse')

        """TRAINING"""
        my_model.fit(X_train, Y_train, validation_data=(X_validate, Y_validate), epochs=30)

        joblib.dump(self.scaler, 'scaler.gz')
        self.predict_next(total_days)

    def predict_next(self, total_days):
        """PREDICTION"""
        my_model = tf.keras.models.load_model('deaths_model')
        self.scaler = joblib.load('scaler.gz')

        # Fetch the list of countries in the correct order from the actual next day data
        actual_next_day_data = self.get_total_dict(total_days + 1)
        countries = list(actual_next_day_data.keys())

        # Get the actual current day's data
        current_day_data = self.get_total_dict(total_days)

        # Remove 'High income' key from the dictionaries
        current_day_data.pop('High income', None)
        actual_next_day_data.pop('High income', None)

        current_day_data.pop('Democratic Republic of the Congo', None)
        actual_next_day_data.pop('Democratic Republic of the Congo', None)


        last_day_data = np.array([self.get_total_list(total_days)])

        last_day_data = self.scaler.transform(last_day_data)
        last_day_data = last_day_data.reshape(1, self.look_back, -1)
        prediction_next_day = my_model.predict(last_day_data)
        prediction_next_day = self.scaler.inverse_transform(prediction_next_day)

        # Extract the first row of predictions and ignore the first value (days_passed)
        next_day_predictions = prediction_next_day[0][1:]  # Skip the first element (days_passed)

        # Replace negative values with zero and map to corresponding countries
        predictions_dict = {country: max(0, int(pred)) for country, pred in zip(countries, next_day_predictions)}

        # Remove 'High income' key from the prediction dictionary
        predictions_dict.pop('High income', None)
        predictions_dict.pop('Democratic Republic of the Congo', None)

        # Calculate the difference in deaths
        death_differences = {country: predictions_dict[country] - current_day_data.get(country, 0)
                             for country in countries if
                             country != 'High income' and country != 'Democratic Republic of the Congo'}
        death_differences_actual = {country: actual_next_day_data[country] - current_day_data.get(country, 0)
                                    for country in countries if
                                    country != 'High income' and country != 'Democratic Republic of the Congo'}

        # print("Total Deaths for the current day:", current_day_data)
       # print("")
       # print("Prediction for the next day:", predictions_dict)
       # print("Death differences from current day (Predicted):", death_differences)

        # For comparison
        #print("Actual data for the next day:", actual_next_day_data)
        #print("Death differences from current day (Actual):", death_differences_actual)

        #print("")
        # Sort the predicted differences and get top 5
        top_5_predicted_diff = sorted(death_differences.items(), key=lambda x: x[1], reverse=True)[:50]

        # Sort the actual differences and get top 5
        top_5_actual_diff = sorted(death_differences_actual.items(), key=lambda x: x[1], reverse=True)[:50]

        top_5_predicted_total_deaths = sorted(predictions_dict.items(), key=lambda x: x[1], reverse=True)[:50]
        top_5_actual_total_deaths = sorted(actual_next_day_data.items(), key=lambda x: x[1], reverse=True)[:50]

        #print("Top 5 predicted death differences from current day:", top_5_predicted_diff)
        #print("Top 5 actual death differences from current day:", top_5_actual_diff)
        #print("")
        #print("")
        #print("Top 5 predicted total deaths for the next day:", top_5_predicted_total_deaths)
        #print("Top 5 actual total deaths for the next day:", top_5_actual_total_deaths)

        return top_5_predicted_total_deaths


"""
neural_processor = NeuralProcessingTesting()
neural_processor.predict_next(1300)
"""