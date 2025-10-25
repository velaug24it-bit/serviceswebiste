from flask import Flask, render_template, request, jsonify, session
from datetime import datetime, timedelta
import uuid
import random
import json
from werkzeug.security import generate_password_hash, check_password_hash

from tamilnadu_workers_6types import providers as initial_providers

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# In-memory databases (replace with SQLite/MySQL in production)
bookings = {}
booking_statuses = {}
registered_users = {}  # email: user_data
registered_providers_list = []  # List of provider dictionaries
providers = initial_providers.copy()  # Start with initial providers

@app.route("/")
def home():
    return render_template("index.html")

# ===== AUTHENTICATION ROUTES =====

@app.route("/api/register/customer", methods=["POST"])
def register_customer():
    try:
        data = request.json
        email = data.get("email")
        
        # Check if email already exists
        if email in registered_users:
            return jsonify({"success": False, "message": "Email already registered"}), 400
        
        # Store user data (in production, hash the password)
        user_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "password": generate_password_hash(data.get("password")),
            "name": data.get("name"),
            "phone": data.get("phone"),
            "location": data.get("location"),
            "userType": "customer",
            "createdAt": datetime.now().isoformat()
        }
        
        registered_users[email] = user_data
        
        return jsonify({
            "success": True,
            "message": "Account created successfully",
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "name": user_data["name"],
                "userType": user_data["userType"]
            }
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/register/provider", methods=["POST"])
def register_provider():
    try:
        data = request.json
        email = data.get("email")
        
        # Check if email already exists
        if email in registered_users:
            return jsonify({"success": False, "message": "Email already registered"}), 400
        
        # Generate unique provider ID
        provider_id = len(providers) + 1
        
        # Create provider data
        provider_data = {
            "id": provider_id,
            "name": data.get("name"),
            "category": data.get("category"),
            "avatar": data.get("avatar", "🔧"),
            "rating": 5.0,
            "reviews": 0,
            "services": data.get("services", []),
            "priceRange": data.get("hourlyRate", "₹500") + "/hour",
            "verified": False,
            "location": data.get("location"),
            "experience": data.get("experience", "0 years"),
            "description": data.get("description", ""),
            "phone": data.get("phone"),
            "email": email,
            "licenseNumber": data.get("licenseNumber", ""),
            "insuranceStatus": data.get("insuranceStatus", "none"),
            "workingDays": data.get("workingDays", []),
            "workingHours": data.get("workingHours", {}),
            "serviceRadius": data.get("serviceRadius", "10 km"),
            "registrationDate": datetime.now().isoformat()
        }
        
        # Add to providers list
        providers.append(provider_data)
        registered_providers_list.append(provider_data)
        
        # Store user credentials
        user_data = {
            "id": str(provider_id),
            "email": email,
            "password": generate_password_hash(data.get("password")),
            "name": data.get("name"),
            "phone": data.get("phone"),
            "userType": "provider",
            "providerId": provider_id,
            "createdAt": datetime.now().isoformat()
        }
        
        registered_users[email] = user_data
        
        return jsonify({
            "success": True,
            "message": "Provider account created successfully",
            "provider": provider_data,
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "name": user_data["name"],
                "userType": user_data["userType"]
            }
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")
        user_type = data.get("userType", "customer")
        
        # Check if user exists
        if email not in registered_users:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
        
        user = registered_users[email]
        
        # Verify password
        if not check_password_hash(user["password"], password):
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
        
        # Check if user type matches
        if user["userType"] != user_type:
            return jsonify({"success": False, "message": "Invalid account type"}), 401
        
        # Create session
        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["user_type"] = user["userType"]
        
        # Return user data (excluding password)
        user_response = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "userType": user["userType"]
        }
        
        # If provider, include provider details
        if user_type == "provider" and "providerId" in user:
            provider = next((p for p in providers if p["id"] == user["providerId"]), None)
            if provider:
                user_response["provider"] = provider
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": user_response
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@app.route("/api/user/current", methods=["GET"])
def get_current_user():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    email = session.get("email")
    if email not in registered_users:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    user = registered_users[email]
    user_response = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "userType": user["userType"]
    }
    
    return jsonify({"success": True, "user": user_response}), 200


# ===== PROVIDER ROUTES =====

@app.route("/providers", methods=["GET"])
def get_providers():
    category = request.args.get("category")
    location = request.args.get("location")
    rating = request.args.get("rating")
    
    filtered_providers = providers
    
    if category:
        filtered_providers = [p for p in filtered_providers if p["category"] == category]
    
    if location:
        filtered_providers = [p for p in filtered_providers if p["location"] == location]
    
    if rating:
        min_rating = float(rating)
        filtered_providers = [p for p in filtered_providers if p["rating"] >= min_rating]
    
    return jsonify(filtered_providers)


@app.route("/providers/<int:provider_id>", methods=["GET"])
def get_provider(provider_id):
    provider = next((p for p in providers if p["id"] == provider_id), None)
    
    if not provider:
        return jsonify({"success": False, "message": "Provider not found"}), 404
    
    return jsonify({"success": True, "provider": provider}), 200


@app.route("/api/provider/update/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    try:
        # Check if user is authenticated and is a provider
        if "user_id" not in session or session.get("user_type") != "provider":
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        data = request.json
        provider = next((p for p in providers if p["id"] == provider_id), None)
        
        if not provider:
            return jsonify({"success": False, "message": "Provider not found"}), 404
        
        # Update provider data
        updatable_fields = ["description", "services", "priceRange", "workingDays", 
                           "workingHours", "serviceRadius", "phone"]
        
        for field in updatable_fields:
            if field in data:
                provider[field] = data[field]
        
        return jsonify({"success": True, "message": "Provider updated successfully", "provider": provider}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/provider/dashboard/<int:provider_id>", methods=["GET"])
def provider_dashboard(provider_id):
    try:
        # Get provider's bookings
        provider_bookings = [b for b in bookings.values() if b.get("providerId") == provider_id]
        
        # Calculate stats
        today = datetime.now().date()
        today_bookings = len([b for b in provider_bookings if datetime.strptime(b["date"], "%Y-%m-%d").date() == today])
        
        completed_bookings = [b for b in provider_bookings if b["status"] == "Completed"]
        total_earnings = sum([float(b["price"].replace("$", "").replace("₹", "")) for b in completed_bookings])
        
        # Get recent bookings (last 5)
        recent_bookings = sorted(provider_bookings, key=lambda x: x["createdAt"], reverse=True)[:5]
        
        return jsonify({
            "success": True,
            "stats": {
                "todayBookings": today_bookings,
                "totalBookings": len(provider_bookings),
                "completedBookings": len(completed_bookings),
                "totalEarnings": total_earnings,
                "averageRating": next((p["rating"] for p in providers if p["id"] == provider_id), 5.0)
            },
            "recentBookings": recent_bookings
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ===== BOOKING ROUTES =====

@app.route("/book", methods=["POST"])
def book_service():
    try:
        data = request.json
        booking_id = "BK" + str(uuid.uuid4().hex[:6]).upper()

        provider_id = data.get("providerId")
        provider = next((p for p in providers if p["id"] == provider_id), None)
        
        if not provider:
            return jsonify({"success": False, "message": "Provider not found"}), 404

        # Generate tracking ID
        tracking_id = f"SH{datetime.now().strftime('%y%m%d')}{random.randint(100, 999)}"

        booking = {
            "id": booking_id,
            "trackingId": tracking_id,
            "providerId": provider_id,
            "providerName": provider["name"],
            "serviceType": data.get("serviceType"),
            "date": data.get("date"),
            "time": data.get("time"),
            "description": data.get("description"),
            "phone": data.get("phone"),
            "location": provider["location"],
            "price": provider["priceRange"].split(" - ")[0] if " - " in provider["priceRange"] else provider["priceRange"].split("/")[0],
            "status": "Confirmed",
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        bookings[booking_id] = booking
        
        # Initialize booking status
        booking_statuses[booking_id] = {
            "status": "confirmed",
            "progress": 10,
            "providerLocation": {
                "lat": 13.0827 if provider["location"] == "Chennai" else 11.0168,
                "lng": 80.2707 if provider["location"] == "Chennai" else 76.9558
            },
            "eta": "45 minutes",
            "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "success": True, 
            "bookingId": booking_id, 
            "booking": booking,
            "trackingId": tracking_id
        }), 201
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/my-bookings", methods=["GET"])
def my_bookings():
    try:
        # Convert bookings to list and reverse to show newest first
        bookings_list = list(bookings.values())
        bookings_list.reverse()
        
        # Add status information to each booking
        for booking in bookings_list:
            booking_id = booking["id"]
            if booking_id in booking_statuses:
                booking["statusInfo"] = booking_statuses[booking_id]
        
        return jsonify(bookings_list), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/track/<booking_id>", methods=["GET"])
def track_service(booking_id):
    try:
        booking = bookings.get(booking_id)
        if booking:
            status_info = booking_statuses.get(booking_id, {})
            return jsonify({
                "success": True, 
                "booking": booking,
                "statusInfo": status_info
            }), 200
        else:
            return jsonify({"success": False, "message": "Booking not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/track/by-tracking-id/<tracking_id>", methods=["GET"])
def track_by_tracking_id(tracking_id):
    try:
        # Find booking by tracking ID
        booking = next((b for b in bookings.values() if b.get("trackingId") == tracking_id), None)
        
        if booking:
            booking_id = booking["id"]
            status_info = booking_statuses.get(booking_id, {})
            return jsonify({
                "success": True, 
                "booking": booking,
                "statusInfo": status_info
            }), 200
        else:
            return jsonify({"success": False, "message": "Booking not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/update-booking-status", methods=["POST"])
def update_booking_status():
    try:
        for booking_id, status_info in booking_statuses.items():
            if status_info["status"] not in ["completed", "cancelled"]:
                # Simulate progress
                if status_info["progress"] < 100:
                    status_info["progress"] += random.randint(5, 15)
                    status_info["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Update status based on progress
                    if status_info["progress"] >= 100:
                        status_info["status"] = "completed"
                        status_info["eta"] = "Service completed"
                        if booking_id in bookings:
                            bookings[booking_id]["status"] = "Completed"
                    elif status_info["progress"] >= 70:
                        status_info["status"] = "in-progress"
                        status_info["eta"] = "15 minutes remaining"
                    elif status_info["progress"] >= 40:
                        status_info["status"] = "en-route"
                        # Simulate moving closer
                        if status_info.get("providerLocation"):
                            status_info["providerLocation"]["lat"] += (random.random() - 0.5) * 0.001
                            status_info["providerLocation"]["lng"] += (random.random() - 0.5) * 0.001
                        status_info["eta"] = "20 minutes"
        
        return jsonify({"success": True, "message": "Booking statuses updated"}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/reschedule/<booking_id>", methods=["POST"])
def reschedule_booking(booking_id):
    try:
        data = request.json
        booking = bookings.get(booking_id)
        
        if not booking:
            return jsonify({"success": False, "message": "Booking not found"}), 404
        
        # Update booking details
        booking["date"] = data.get("date", booking["date"])
        booking["time"] = data.get("time", booking["time"])
        
        # Update status
        if booking_id in booking_statuses:
            booking_statuses[booking_id]["status"] = "confirmed"
            booking_statuses[booking_id]["progress"] = 10
            booking_statuses[booking_id]["eta"] = "Rescheduled - 45 minutes"
            booking_statuses[booking_id]["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({"success": True, "booking": booking}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/cancel/<booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    try:
        booking = bookings.get(booking_id)
        
        if not booking:
            return jsonify({"success": False, "message": "Booking not found"}), 404
        
        # Update booking status
        booking["status"] = "Cancelled"
        
        # Update status tracking
        if booking_id in booking_statuses:
            booking_statuses[booking_id]["status"] = "cancelled"
            booking_statuses[booking_id]["progress"] = 0
            booking_statuses[booking_id]["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({"success": True, "booking": booking}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/clear-bookings", methods=["POST"])
def clear_bookings():
    try:
        bookings.clear()
        booking_statuses.clear()
        return jsonify({"success": True, "message": "All bookings cleared"}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ===== UTILITY ROUTES =====

@app.route("/categories", methods=["GET"])
def get_categories():
    try:
        categories = list(set(provider["category"] for provider in providers))
        return jsonify(categories), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/locations", methods=["GET"])
def get_locations():
    try:
        locations = list(set(provider["location"] for provider in providers))
        return jsonify(locations), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        stats = {
            "totalProviders": len(providers),
            "totalBookings": len(bookings),
            "activeBookings": len([b for b in bookings.values() if b["status"] not in ["Completed", "Cancelled"]]),
            "completedBookings": len([b for b in bookings.values() if b["status"] == "Completed"]),
            "registeredCustomers": len([u for u in registered_users.values() if u["userType"] == "customer"]),
            "registeredProviders": len([u for u in registered_users.values() if u["userType"] == "provider"])
        }
        
        return jsonify({"success": True, "stats": stats}), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "message": "Resource not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)